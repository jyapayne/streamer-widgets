from __future__ import annotations

import asyncio
from typing import Optional

from app.chat_models import Platform
from app.providers.twitch_chat import TwitchChatClient
from app.providers.youtube_chat import YouTubeChatClient
from app.state import AppState


class ChatManager:
    """
    Manages chat connections to Twitch and YouTube.
    Starts/stops clients based on configuration.
    """

    def __init__(self, state: AppState):
        self.state = state
        self.twitch_client: Optional[TwitchChatClient] = None
        self.youtube_client: Optional[YouTubeChatClient] = None
        self.twitch_task: Optional[asyncio.Task] = None
        self.youtube_task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """Start chat clients based on current configuration."""
        config = self.state.chat_config

        # Start Twitch if configured
        if config.twitch_channel:
            twitch_tokens = await self.state.get_auth_tokens(Platform.TWITCH)
            if twitch_tokens or True:  # Allow anonymous connection
                await self.start_twitch(config.twitch_channel)

        # Start YouTube if authenticated (video_id is optional - can auto-detect)
        youtube_tokens = await self.state.get_auth_tokens(Platform.YOUTUBE)
        if youtube_tokens:
            # Pass video_id if provided, otherwise YouTubeChatClient will auto-detect
            await self.start_youtube(config.youtube_video_id or None)

    async def stop(self) -> None:
        """Stop all chat clients."""
        await self.stop_twitch()
        await self.stop_youtube()

    async def start_twitch(self, channel: str) -> None:
        """Start Twitch chat client."""
        await self.stop_twitch()

        self.twitch_client = TwitchChatClient(self.state, channel)
        self.twitch_task = asyncio.create_task(self.twitch_client.start())
        print(f"Started Twitch chat for channel: {channel}")

    async def stop_twitch(self) -> None:
        """Stop Twitch chat client."""
        if self.twitch_client:
            await self.twitch_client.stop()
            self.twitch_client = None

        if self.twitch_task and not self.twitch_task.done():
            self.twitch_task.cancel()
            try:
                await self.twitch_task
            except asyncio.CancelledError:
                pass
            self.twitch_task = None

    async def start_youtube(self, video_id: Optional[str] = None) -> None:
        """Start YouTube chat client."""
        await self.stop_youtube()

        self.youtube_client = YouTubeChatClient(self.state, video_id)
        self.youtube_task = asyncio.create_task(self.youtube_client.start())
        if video_id:
            print(f"Started YouTube chat for video: {video_id}")
        else:
            print("Started YouTube chat (auto-detecting active broadcast)")

    async def stop_youtube(self) -> None:
        """Stop YouTube chat client."""
        if self.youtube_client:
            await self.youtube_client.stop()
            self.youtube_client = None

        if self.youtube_task and not self.youtube_task.done():
            self.youtube_task.cancel()
            try:
                await self.youtube_task
            except asyncio.CancelledError:
                pass
            self.youtube_task = None

    async def restart(self) -> None:
        """Restart all chat clients with current configuration."""
        await self.stop()
        await self.start()

    async def send_message(self, platform: Platform | str, message: str) -> tuple[bool, str]:
        """
        Send a chat message to the specified platform(s).
        
        Platform can be Platform.TWITCH, Platform.YOUTUBE, or "all" to send to both.
        Returns a tuple of (success, error_message).
        """
        # Handle sending to all platforms
        if platform == "all":
            return await self._send_to_all(message)
        
        if platform == Platform.TWITCH:
            if not self.twitch_client:
                return False, "Twitch chat not connected"
            if not self.twitch_client.is_authenticated:
                return False, "Not authenticated. Go to /config, login with Twitch, then restart the app."
            success = await self.twitch_client.send_message(message)
            if success:
                return True, ""
            return False, "Failed to send message"
        
        elif platform == Platform.YOUTUBE:
            if not self.youtube_client:
                return False, "YouTube chat not connected"
            if not self.youtube_client.live_chat_id:
                return False, "No active YouTube live chat found"
            success = await self.youtube_client.send_message(message)
            if success:
                return True, ""
            return False, "Failed to send message"
        
        return False, f"Unknown platform: {platform}"

    async def _send_to_all(self, message: str) -> tuple[bool, str]:
        """Send a message to all connected platforms with a single echo."""
        errors = []
        any_success = False
        echoed = False
        
        # Try Twitch
        if self.twitch_client and self.twitch_client.is_authenticated:
            # Send without echo first
            success = await self.twitch_client.send_message_no_echo(message)
            if success:
                any_success = True
                # Echo once from Twitch (since it has better user info)
                if not echoed:
                    await self.twitch_client._echo_sent_message(message)
                    echoed = True
            else:
                errors.append("Twitch: failed to send")
        
        # Try YouTube
        if self.youtube_client and self.youtube_client.live_chat_id:
            success = await self.youtube_client.send_message(message)
            if success:
                any_success = True
            else:
                errors.append("YouTube: failed to send")
        
        if any_success:
            if errors:
                return True, f"Sent (some failed: {', '.join(errors)})"
            return True, ""
        
        if errors:
            return False, "; ".join(errors)
        return False, "No platforms connected"