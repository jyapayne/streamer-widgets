from __future__ import annotations

import asyncio
from collections import deque
from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional, Set

from app.chat_models import AuthTokens, ChatConfig, ChatMessage, Platform


@dataclass
class NowPlaying:
    title: str = ""
    album: str = ""
    artist: str = ""
    playing: bool = False
    source_app: str = ""
    art_url: str = "/art/album.png"
    has_art: bool = False
    updated_unix: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class AppState:
    """
    Shared state + websocket client tracking.
    """

    def __init__(self) -> None:
        self.now_playing: NowPlaying = NowPlaying()
        self._ws_clients: Set[Any] = set()
        self._lock = asyncio.Lock()

        # Chat state
        self.chat_messages: deque[ChatMessage] = deque(maxlen=100)
        self.chat_config: ChatConfig = ChatConfig()
        self.twitch_tokens: Optional[AuthTokens] = None
        self.youtube_tokens: Optional[AuthTokens] = None
        
        # Chat manager reference (set by main.py after creation)
        self.chat_manager: Optional[Any] = None

    async def set_now_playing(self, np: NowPlaying) -> None:
        async with self._lock:
            self.now_playing = np

    async def get_now_playing(self) -> NowPlaying:
        async with self._lock:
            return self.now_playing

    async def register_ws(self, ws: Any) -> None:
        async with self._lock:
            self._ws_clients.add(ws)

    async def unregister_ws(self, ws: Any) -> None:
        async with self._lock:
            self._ws_clients.discard(ws)

    async def broadcast(self, message: Dict[str, Any]) -> None:
        async with self._lock:
            clients = list(self._ws_clients)

        dead: list[Any] = []
        for ws in clients:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)

        if dead:
            async with self._lock:
                for ws in dead:
                    self._ws_clients.discard(ws)

    async def add_chat_message(self, message: ChatMessage) -> None:
        """Add a chat message and broadcast to all connected clients."""
        async with self._lock:
            self.chat_messages.append(message)

        await self.broadcast({
            "type": "chat_message",
            "data": message.to_dict(),
        })

    async def get_chat_messages(self, limit: int = 50) -> list[ChatMessage]:
        """Get recent chat messages."""
        async with self._lock:
            messages = list(self.chat_messages)
            return messages[-limit:] if limit else messages

    async def set_auth_tokens(self, platform: Platform, tokens: AuthTokens) -> None:
        """Store authentication tokens for a platform."""
        async with self._lock:
            if platform == Platform.TWITCH:
                self.twitch_tokens = tokens
            elif platform == Platform.YOUTUBE:
                self.youtube_tokens = tokens

    async def get_auth_tokens(self, platform: Platform) -> Optional[AuthTokens]:
        """Retrieve authentication tokens for a platform."""
        async with self._lock:
            if platform == Platform.TWITCH:
                return self.twitch_tokens
            elif platform == Platform.YOUTUBE:
                return self.youtube_tokens
            return None

    async def update_chat_config(self, config: ChatConfig) -> None:
        """Update chat configuration."""
        async with self._lock:
            self.chat_config = config


