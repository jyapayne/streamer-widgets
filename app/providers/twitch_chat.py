from __future__ import annotations

import asyncio
import re
from datetime import datetime
from typing import Optional

import aiohttp

from app.chat_models import ChatBadge, ChatMessage, ChatUser, Emote, Platform, UserRole
from app.state import AppState


class TwitchChatClient:
    """
    Twitch IRC WebSocket client for reading chat messages.
    Uses anonymous IRC connection or authenticated if token is provided.
    """

    IRC_WS_URL = "wss://irc-ws.chat.twitch.tv:443"

    def __init__(self, state: AppState, channel: str):
        self.state = state
        self.channel = channel.lower().lstrip("#")
        self.ws: Optional[aiohttp.ClientWebSocket] = None
        self.session: Optional[aiohttp.ClientSession] = None
        self.running = False

        # Emote caches
        self.global_emotes: dict[str, Emote] = {}
        self.channel_emotes: dict[str, Emote] = {}
        
        # Badge caches: badge_name/version -> image_url
        self.global_badges: dict[str, str] = {}
        self.channel_badges: dict[str, str] = {}
        self.channel_id: Optional[str] = None

    async def start(self) -> None:
        """Start the IRC connection."""
        self.running = True
        self.session = aiohttp.ClientSession()

        tokens = await self.state.get_auth_tokens(Platform.TWITCH)

        try:
            # Get channel ID for badges and emotes
            await self._get_channel_id()
            
            # Load badges
            await self._load_badges()
            
            # Load emotes
            await self._load_emotes()

            # Connect to IRC
            self.ws = await self.session.ws_connect(self.IRC_WS_URL)

            # Authenticate
            if tokens and tokens.access_token:
                await self.ws.send_str(f"PASS oauth:{tokens.access_token}")
                await self.ws.send_str(f"NICK {self.channel}")
            else:
                # Anonymous connection
                await self.ws.send_str("PASS SCHMOOPIIE")
                await self.ws.send_str(f"NICK justinfan{asyncio.get_event_loop().time():.0f}")

            # Request capabilities for tags (emotes, badges, color, etc.)
            await self.ws.send_str("CAP REQ :twitch.tv/tags twitch.tv/commands")

            # Join channel
            await self.ws.send_str(f"JOIN #{self.channel}")

            # Start message loop
            await self._message_loop()

        except Exception as e:
            print(f"Twitch chat error: {e}")
        finally:
            await self.stop()

    async def stop(self) -> None:
        """Stop the IRC connection."""
        self.running = False
        if self.ws:
            await self.ws.close()
        if self.session:
            await self.session.close()

    async def _message_loop(self) -> None:
        """Main loop to receive and process IRC messages."""
        if not self.ws:
            return

        async for msg in self.ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                await self._handle_irc_message(msg.data)
            elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                break

    async def _handle_irc_message(self, raw: str) -> None:
        """Parse and handle a single IRC message."""
        raw = raw.strip()

        # Respond to PING
        if raw.startswith("PING"):
            if self.ws:
                await self.ws.send_str("PONG :tmi.twitch.tv")
            return

        # Parse PRIVMSG (chat messages)
        if "PRIVMSG" in raw:
            await self._parse_privmsg(raw)

    async def _parse_privmsg(self, raw: str) -> None:
        """
        Parse a PRIVMSG IRC line.
        Format: @tags :user!user@user.tmi.twitch.tv PRIVMSG #channel :message
        """
        # Extract tags
        tags = {}
        if raw.startswith("@"):
            tag_str, raw = raw.split(" ", 1)
            for tag in tag_str[1:].split(";"):
                if "=" in tag:
                    key, value = tag.split("=", 1)
                    tags[key] = value

        # Extract user
        user_match = re.search(r":(\w+)!", raw)
        if not user_match:
            return
        username = user_match.group(1)

        # Extract message
        msg_match = re.search(r"PRIVMSG #\w+ :(.+)", raw)
        if not msg_match:
            return
        message_text = msg_match.group(1)

        # Check for /me action
        is_action = message_text.startswith("\x01ACTION") and message_text.endswith("\x01")
        if is_action:
            message_text = message_text[8:-1].strip()

        # Build user object
        user = self._build_user(username, tags)

        # Build message object
        msg_id = tags.get("id", f"{username}_{datetime.now().timestamp()}")
        emotes = await self._parse_emotes(message_text, tags)

        chat_msg = ChatMessage(
            id=msg_id,
            platform=Platform.TWITCH,
            user=user,
            message=message_text,
            timestamp=datetime.now(),
            emotes=emotes,
            is_action=is_action,
        )

        # Add to state
        await self.state.add_chat_message(chat_msg)

    def _build_user(self, username: str, tags: dict[str, str]) -> ChatUser:
        """Build a ChatUser from IRC tags."""
        display_name = tags.get("display-name", username)
        user_id = tags.get("user-id", username)
        color = tags.get("color") or None

        # Parse roles
        roles = [UserRole.VIEWER]
        badges_tag = tags.get("badges", "")

        if "broadcaster" in badges_tag:
            roles.append(UserRole.BROADCASTER)
        if "moderator" in badges_tag:
            roles.append(UserRole.MODERATOR)
        if "vip" in badges_tag:
            roles.append(UserRole.VIP)
        if "subscriber" in badges_tag or "founder" in badges_tag:
            roles.append(UserRole.SUBSCRIBER)

        # Parse badges with icons
        badges = []
        if badges_tag:
            for badge_pair in badges_tag.split(","):
                if "/" in badge_pair:
                    badge_name, badge_version = badge_pair.split("/", 1)
                    badge_key = f"{badge_name}/{badge_version}"
                    
                    # Look up badge image URL (channel badges first, then global)
                    icon_url = self.channel_badges.get(badge_key) or self.global_badges.get(badge_key)
                    
                    badges.append(ChatBadge(name=badge_name, icon_url=icon_url))

        return ChatUser(
            id=user_id,
            username=username,
            display_name=display_name,
            platform=Platform.TWITCH,
            color=color,
            roles=roles,
            badges=badges,
        )
    
    async def _get_channel_id(self) -> None:
        """Get the channel's Twitch user ID (needed for badges/emotes)."""
        if not self.session:
            return
            
        try:
            # Use the unofficial Twitch API to get user ID from username
            url = f"https://api.ivr.fi/v2/twitch/user?login={self.channel}"
            async with self.session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data and len(data) > 0:
                        self.channel_id = data[0].get("id")
                        print(f"Twitch: Got channel ID {self.channel_id} for {self.channel}")
        except Exception as e:
            print(f"Twitch: Error getting channel ID: {e}")
    
    async def _load_badges(self) -> None:
        """Load Twitch badges (global and channel-specific) using Helix API."""
        if not self.session:
            return
        
        # Get OAuth config for Client-ID
        from app.config import load_config
        config = load_config()
        client_id = config.twitch_oauth.client_id
        
        # Get access token if available
        tokens = await self.state.get_auth_tokens(Platform.TWITCH)
        
        headers = {}
        if client_id:
            headers["Client-ID"] = client_id
        if tokens and tokens.access_token:
            headers["Authorization"] = f"Bearer {tokens.access_token}"
            
        try:
            # Load global badges via Helix API
            if headers:
                async with self.session.get(
                    "https://api.twitch.tv/helix/chat/badges/global",
                    headers=headers
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        for badge_set in data.get("data", []):
                            badge_name = badge_set.get("set_id")
                            for version in badge_set.get("versions", []):
                                version_id = version.get("id")
                                badge_key = f"{badge_name}/{version_id}"
                                # Prefer higher resolution images
                                icon_url = (
                                    version.get("image_url_4x") or
                                    version.get("image_url_2x") or
                                    version.get("image_url_1x")
                                )
                                if icon_url:
                                    self.global_badges[badge_key] = icon_url
                        print(f"Twitch: Loaded {len(self.global_badges)} global badges")
                    else:
                        print(f"Twitch: Failed to load global badges (status {resp.status})")
                
                # Load channel badges if we have channel ID
                if self.channel_id:
                    async with self.session.get(
                        f"https://api.twitch.tv/helix/chat/badges?broadcaster_id={self.channel_id}",
                        headers=headers
                    ) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            for badge_set in data.get("data", []):
                                badge_name = badge_set.get("set_id")
                                for version in badge_set.get("versions", []):
                                    version_id = version.get("id")
                                    badge_key = f"{badge_name}/{version_id}"
                                    icon_url = (
                                        version.get("image_url_4x") or
                                        version.get("image_url_2x") or
                                        version.get("image_url_1x")
                                    )
                                    if icon_url:
                                        self.channel_badges[badge_key] = icon_url
                            print(f"Twitch: Loaded {len(self.channel_badges)} channel badges")
            else:
                # Fallback: use static badge URLs for common badges if no OAuth
                self._load_static_badges()
                        
        except Exception as e:
            print(f"Twitch: Error loading badges: {e}")
            # Fallback to static badges
            self._load_static_badges()
    
    def _load_static_badges(self) -> None:
        """Load static fallback badges for common badge types."""
        # These are stable CDN URLs for common Twitch badges
        static_badges = {
            "broadcaster/1": "https://static-cdn.jtvnw.net/badges/v1/5527c58c-fb7d-422d-b71b-f309dcb85cc1/3",
            "moderator/1": "https://static-cdn.jtvnw.net/badges/v1/3267646d-33f0-4b17-b3df-f923a41db1d0/3",
            "vip/1": "https://static-cdn.jtvnw.net/badges/v1/b817aba4-fad8-49e2-b88a-7cc744f6a6e3/3",
            "subscriber/0": "https://static-cdn.jtvnw.net/badges/v1/5d9f2208-5dd8-11e7-8513-2ff4adfae661/3",
            "subscriber/1": "https://static-cdn.jtvnw.net/badges/v1/5d9f2208-5dd8-11e7-8513-2ff4adfae661/3",
            "premium/1": "https://static-cdn.jtvnw.net/badges/v1/bbbe0db0-a598-423e-86d0-f9fb98ca1933/3",
            "partner/1": "https://static-cdn.jtvnw.net/badges/v1/d12a2e27-16f6-41d0-ab77-b780518f00a3/3",
            "turbo/1": "https://static-cdn.jtvnw.net/badges/v1/bd444ec6-8f34-4bf9-91f4-af1e3428d80f/3",
            "glhf-pledge/1": "https://static-cdn.jtvnw.net/badges/v1/3158e758-3cb4-43c5-94b3-7571f71cf6a0/3",
            "founder/0": "https://static-cdn.jtvnw.net/badges/v1/511b78a9-ab37-472f-9569-457753bbe7d3/3",
        }
        self.global_badges.update(static_badges)
        print(f"Twitch: Loaded {len(static_badges)} static fallback badges")

    async def _parse_emotes(self, message: str, tags: dict[str, str]) -> list[Emote]:
        """Parse emotes from message and tags."""
        emotes = []

        # Parse Twitch native emotes from tags
        emotes_tag = tags.get("emotes", "")
        if emotes_tag:
            # Format: "emoteid:start-end,start-end/emoteid2:start-end"
            for emote_data in emotes_tag.split("/"):
                if ":" not in emote_data:
                    continue
                emote_id, positions = emote_data.split(":", 1)
                # Just use first position to get the code
                if "-" in positions:
                    start_pos = int(positions.split(",")[0].split("-")[0])
                    end_pos = int(positions.split(",")[0].split("-")[1])
                    code = message[start_pos : end_pos + 1]
                    emotes.append(
                        Emote(
                            code=code,
                            url=f"https://static-cdn.jtvnw.net/emoticons/v2/{emote_id}/default/dark/1.0",
                            provider="twitch",
                        )
                    )

        # Check for third-party emotes in message
        words = message.split()
        for word in words:
            # Check FFZ
            if word in self.global_emotes or word in self.channel_emotes:
                emote = self.global_emotes.get(word) or self.channel_emotes.get(word)
                if emote and emote not in emotes:
                    emotes.append(emote)

        return emotes

    async def _load_emotes(self) -> None:
        """Load third-party emotes from FFZ, BTTV, 7TV."""
        config = self.state.chat_config

        if not self.session:
            return

        try:
            # Load FrankerFaceZ emotes
            if config.enable_ffz:
                await self._load_ffz_emotes()

            # Load BTTV emotes
            if config.enable_bttv:
                await self._load_bttv_emotes()

            # Load 7TV emotes
            if config.enable_7tv:
                await self._load_7tv_emotes()

        except Exception as e:
            print(f"Error loading emotes: {e}")

    async def _load_ffz_emotes(self) -> None:
        """Load FrankerFaceZ emotes for the channel."""
        if not self.session:
            return

        try:
            # Global FFZ emotes
            async with self.session.get("https://api.frankerfacez.com/v1/set/global") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    for set_id, set_data in data.get("sets", {}).items():
                        for emote in set_data.get("emoticons", []):
                            code = emote.get("name")
                            urls = emote.get("urls", {})
                            url = urls.get("4") or urls.get("2") or urls.get("1")
                            if code and url:
                                self.global_emotes[code] = Emote(
                                    code=code, url=f"https:{url}" if url.startswith("//") else url, provider="ffz"
                                )

            # Channel-specific FFZ emotes
            async with self.session.get(f"https://api.frankerfacez.com/v1/room/{self.channel}") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    for set_id, set_data in data.get("sets", {}).items():
                        for emote in set_data.get("emoticons", []):
                            code = emote.get("name")
                            urls = emote.get("urls", {})
                            url = urls.get("4") or urls.get("2") or urls.get("1")
                            if code and url:
                                self.channel_emotes[code] = Emote(
                                    code=code, url=f"https:{url}" if url.startswith("//") else url, provider="ffz"
                                )
        except Exception as e:
            print(f"FFZ emote load error: {e}")

    async def _load_bttv_emotes(self) -> None:
        """Load BetterTTV emotes."""
        if not self.session:
            return

        try:
            # Global BTTV emotes
            async with self.session.get("https://api.betterttv.net/3/cached/emotes/global") as resp:
                if resp.status == 200:
                    emotes = await resp.json()
                    for emote in emotes:
                        code = emote.get("code")
                        emote_id = emote.get("id")
                        if code and emote_id:
                            self.global_emotes[code] = Emote(
                                code=code,
                                url=f"https://cdn.betterttv.net/emote/{emote_id}/1x",
                                provider="bttv",
                            )

            # Channel BTTV emotes
            async with self.session.get(f"https://api.betterttv.net/3/cached/users/twitch/{self.channel}") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    for emote in data.get("channelEmotes", []) + data.get("sharedEmotes", []):
                        code = emote.get("code")
                        emote_id = emote.get("id")
                        if code and emote_id:
                            self.channel_emotes[code] = Emote(
                                code=code,
                                url=f"https://cdn.betterttv.net/emote/{emote_id}/1x",
                                provider="bttv",
                            )
        except Exception as e:
            print(f"BTTV emote load error: {e}")

    async def _load_7tv_emotes(self) -> None:
        """Load 7TV emotes."""
        if not self.session:
            return

        try:
            # Global 7TV emotes
            async with self.session.get("https://7tv.io/v3/emote-sets/global") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    for emote in data.get("emotes", []):
                        code = emote.get("name")
                        emote_data = emote.get("data", {})
                        host = emote_data.get("host", {})
                        if code and host:
                            url = f"https:{host.get('url', '')}/1x.webp"
                            self.global_emotes[code] = Emote(
                                code=code,
                                url=url,
                                provider="7tv",
                                is_animated=emote.get("animated", False),
                            )

            # Channel 7TV emotes
            async with self.session.get(f"https://7tv.io/v3/users/twitch/{self.channel}") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    emote_set = data.get("emote_set", {})
                    for emote in emote_set.get("emotes", []):
                        code = emote.get("name")
                        emote_data = emote.get("data", {})
                        host = emote_data.get("host", {})
                        if code and host:
                            url = f"https:{host.get('url', '')}/1x.webp"
                            self.channel_emotes[code] = Emote(
                                code=code,
                                url=url,
                                provider="7tv",
                                is_animated=emote.get("animated", False),
                            )
        except Exception as e:
            print(f"7TV emote load error: {e}")
