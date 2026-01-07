from __future__ import annotations

import asyncio
from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional, Set


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


