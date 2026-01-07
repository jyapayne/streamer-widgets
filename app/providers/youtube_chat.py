from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Optional

import aiohttp

from app.chat_models import ChatBadge, ChatMessage, ChatUser, Emote, Platform, UserRole
from app.state import AppState


class YouTubeChatClient:
    """
    YouTube Live Chat API client for reading chat messages.
    Uses polling to fetch new messages.
    """

    API_BASE = "https://www.googleapis.com/youtube/v3"

    def __init__(self, state: AppState, video_id: Optional[str] = None):
        self.state = state
        self.video_id = video_id  # Optional - can auto-detect if not provided
        self.session: Optional[aiohttp.ClientSession] = None
        self.running = False

        self.live_chat_id: Optional[str] = None
        self.next_page_token: Optional[str] = None
        self.poll_interval_ms = 2000
        self.broadcast_title: Optional[str] = None

    async def start(self) -> None:
        """Start polling for chat messages."""
        self.running = True
        self.session = aiohttp.ClientSession()

        tokens = await self.state.get_auth_tokens(Platform.YOUTUBE)
        if not tokens or not tokens.access_token:
            print("YouTube: No auth tokens available")
            return

        try:
            # If no video ID provided, try to find user's active broadcast
            if not self.video_id:
                await self._find_active_broadcast(tokens.access_token)
            
            # Get the live chat ID from the video
            if self.video_id:
                await self._get_live_chat_id(tokens.access_token)

            if not self.live_chat_id:
                print("YouTube: Could not find live chat (no active broadcast or invalid video ID)")
                return

            print(f"YouTube: Connected to live chat" + (f" for '{self.broadcast_title}'" if self.broadcast_title else ""))
            
            # Start polling
            await self._poll_loop(tokens.access_token)

        except Exception as e:
            print(f"YouTube chat error: {e}")
        finally:
            await self.stop()

    async def stop(self) -> None:
        """Stop the polling loop."""
        self.running = False
        if self.session:
            await self.session.close()

    async def _find_active_broadcast(self, access_token: str) -> None:
        """Find the user's active live broadcast automatically."""
        if not self.session:
            return

        url = f"{self.API_BASE}/liveBroadcasts"
        params = {
            "part": "id,snippet,status",
            "mine": "true",
            "broadcastStatus": "active",  # Only get currently live broadcasts
        }
        headers = {"Authorization": f"Bearer {access_token}"}

        try:
            async with self.session.get(url, params=params, headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    items = data.get("items", [])
                    
                    if items:
                        # Use the first active broadcast
                        broadcast = items[0]
                        self.video_id = broadcast.get("id")
                        self.broadcast_title = broadcast.get("snippet", {}).get("title")
                        print(f"YouTube: Found active broadcast: {self.broadcast_title}")
                    else:
                        print("YouTube: No active broadcasts found for your channel")
                else:
                    error = await resp.text()
                    print(f"YouTube: Error finding broadcasts: {resp.status} - {error}")
        except Exception as e:
            print(f"YouTube: Error finding active broadcast: {e}")

    async def _get_live_chat_id(self, access_token: str) -> None:
        """Fetch the live chat ID for a video."""
        if not self.session or not self.video_id:
            return

        url = f"{self.API_BASE}/videos"
        params = {
            "part": "liveStreamingDetails,snippet",
            "id": self.video_id,
        }
        headers = {"Authorization": f"Bearer {access_token}"}

        try:
            async with self.session.get(url, params=params, headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    items = data.get("items", [])
                    if items:
                        video = items[0]
                        live_details = video.get("liveStreamingDetails", {})
                        self.live_chat_id = live_details.get("activeLiveChatId")
                        if not self.broadcast_title:
                            self.broadcast_title = video.get("snippet", {}).get("title")
        except Exception as e:
            print(f"YouTube: Error fetching live chat ID: {e}")

    async def _poll_loop(self, access_token: str) -> None:
        """Main polling loop to fetch chat messages."""
        while self.running:
            try:
                await self._fetch_messages(access_token)
                await asyncio.sleep(self.poll_interval_ms / 1000)
            except Exception as e:
                print(f"YouTube: Poll error: {e}")
                await asyncio.sleep(5)

    async def _fetch_messages(self, access_token: str) -> None:
        """Fetch new chat messages from the API."""
        if not self.session or not self.live_chat_id:
            return

        url = f"{self.API_BASE}/liveChat/messages"
        params = {
            "liveChatId": self.live_chat_id,
            "part": "snippet,authorDetails",
        }

        if self.next_page_token:
            params["pageToken"] = self.next_page_token

        headers = {"Authorization": f"Bearer {access_token}"}

        try:
            async with self.session.get(url, params=params, headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()

                    # Update pagination
                    self.next_page_token = data.get("nextPageToken")
                    self.poll_interval_ms = data.get("pollingIntervalMillis", 2000)

                    # Process messages
                    for item in data.get("items", []):
                        await self._process_message(item)

        except Exception as e:
            print(f"YouTube: Error fetching messages: {e}")

    async def _process_message(self, item: dict) -> None:
        """Process a single message item from the API."""
        snippet = item.get("snippet", {})
        author_details = item.get("authorDetails", {})

        msg_type = snippet.get("type")
        if msg_type != "textMessageEvent":
            # Skip super chats, memberships, etc. for now
            return

        # Extract message data
        message_id = item.get("id", "")
        message_text = snippet.get("textMessageDetails", {}).get("messageText", "")
        published_at_str = snippet.get("publishedAt", "")

        # Parse timestamp
        try:
            timestamp = datetime.fromisoformat(published_at_str.replace("Z", "+00:00"))
        except Exception:
            timestamp = datetime.now()

        # Build user
        user = self._build_user(author_details)

        # Build message
        chat_msg = ChatMessage(
            id=message_id,
            platform=Platform.YOUTUBE,
            user=user,
            message=message_text,
            timestamp=timestamp,
            emotes=[],  # YouTube uses standard emoji, could parse later
        )

        # Add to state
        await self.state.add_chat_message(chat_msg)

    def _build_user(self, author_details: dict) -> ChatUser:
        """Build a ChatUser from YouTube author details."""
        user_id = author_details.get("channelId", "")
        username = author_details.get("channelUrl", "").split("/")[-1] or user_id
        display_name = author_details.get("displayName", username)

        # Parse roles
        roles = [UserRole.VIEWER]
        is_owner = author_details.get("isChatOwner", False)
        is_moderator = author_details.get("isChatModerator", False)
        is_sponsor = author_details.get("isChatSponsor", False)

        if is_owner:
            roles.append(UserRole.BROADCASTER)
        if is_moderator:
            roles.append(UserRole.MODERATOR)
        if is_sponsor:
            roles.append(UserRole.SUBSCRIBER)

        # Parse badges
        badges = []
        if is_owner:
            badges.append(ChatBadge(name="owner"))
        if is_moderator:
            badges.append(ChatBadge(name="moderator"))
        if is_sponsor:
            badges.append(ChatBadge(name="member"))

        return ChatUser(
            id=user_id,
            username=username,
            display_name=display_name,
            platform=Platform.YOUTUBE,
            color=None,  # YouTube doesn't provide user colors
            roles=roles,
            badges=badges,
        )
