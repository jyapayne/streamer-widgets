from __future__ import annotations

import asyncio
import base64
import os
import re
import time
from pathlib import Path
from typing import Any, Tuple

from winsdk.windows.media.control import (
    GlobalSystemMediaTransportControlsSessionManager as SessionManager,
    GlobalSystemMediaTransportControlsSessionPlaybackStatus as PlaybackStatus,
)
from winsdk.windows.storage.streams import DataReader

from app.paths import get_art_dir
from app.state import AppState, NowPlaying


ART_FILENAME = "album.png"  # overwritten when track changes
PLACEHOLDER_FILENAME = "placeholder.png"
PLACEHOLDER_PNG_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAwUBAO+X2F8A"
    "AAAASUVORK5CYII="
)


def _write_placeholder(out_path: Path) -> None:
    data = base64.b64decode(PLACEHOLDER_PNG_B64)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(data)


def ensure_art_files(art_dir: Path) -> None:
    placeholder_path = art_dir / PLACEHOLDER_FILENAME
    if not placeholder_path.exists():
        _write_placeholder(placeholder_path)

    album_path = art_dir / ART_FILENAME
    if not album_path.exists():
        _write_placeholder(album_path)


async def _read_thumbnail_to_file(session: Any, out_path: Path) -> bool:
    try:
        media_props = await session.try_get_media_properties_async()
        thumb_ref = media_props.thumbnail
        if thumb_ref is None:
            return False

        stream = await thumb_ref.open_read_async()
        size = int(stream.size or 0)
        if size <= 0:
            return False

        reader = DataReader(stream)
        await reader.load_async(size)
        buffer = bytearray(size)
        reader.read_bytes(buffer)
        out_path.write_bytes(buffer)
        return True
    except Exception:
        return False


def _pick_best_session(sessions: Any) -> Any:
    best = None
    for s in sessions:
        try:
            info = s.get_playback_info()
            status = info.playback_status if info else None
            if status == PlaybackStatus.PLAYING:
                return s
            if best is None:
                best = s
        except Exception:
            continue
    return best


def _extract_album_from_artist(artist_raw: str) -> Tuple[str, str]:
    """
    Extract album info from artist string if embedded.
    
    Supports formats:
    - "Artist [ALBUM:Album Name]" -> ("Artist", "Album Name")
    - "Artist — Album Name" -> ("Artist", "Album Name")  (em dash)
    - "Artist - Album Name" -> ("Artist", "Album Name")  (hyphen with spaces)
    """
    if not artist_raw:
        return "", ""
    
    # First, check for [ALBUM:...] pattern
    m = re.search(r"\s*\[ALBUM:(.*?)\]\s*$", artist_raw, re.IGNORECASE)
    if m:
        album_hint = m.group(1).strip()
        clean_artist = artist_raw[: m.start()].strip()
        return clean_artist, album_hint
    
    # Check for em dash (—) or en dash (–) separator
    for dash in ["—", "–"]:
        if dash in artist_raw:
            parts = artist_raw.split(dash, 1)
            if len(parts) == 2:
                artist = parts[0].strip()
                album = parts[1].strip()
                if artist and album:
                    return artist, album
    
    # Check for spaced hyphen " - " separator (but not "Artist-Name")
    if " - " in artist_raw:
        parts = artist_raw.split(" - ", 1)
        if len(parts) == 2:
            artist = parts[0].strip()
            album = parts[1].strip()
            if artist and album:
                return artist, album
    
    return artist_raw.strip(), ""


async def run_gsmtc_provider(state: AppState) -> None:
    """
    Poll GSMTC and push state updates + broadcast over websocket.
    """
    art_dir = get_art_dir()
    ensure_art_files(art_dir)

    last_art_sig: str | None = None
    last_has_art = False

    while True:
        try:
            manager = await SessionManager.request_async()
            sessions = manager.get_sessions()
            session = _pick_best_session(sessions)

            if session is None:
                _write_placeholder(art_dir / ART_FILENAME)
                last_art_sig = None
                last_has_art = False
                np = NowPlaying(updated_unix=int(time.time()))
                await state.set_now_playing(np)
                await state.broadcast({"type": "nowplaying", "data": np.to_dict()})
                await asyncio.sleep(1)
                continue

            app_id = ""
            try:
                app_id = session.source_app_user_model_id or ""
            except Exception:
                pass

            info = session.get_playback_info()
            status = info.playback_status if info else None
            playing = status == PlaybackStatus.PLAYING

            props = await session.try_get_media_properties_async()

            title = getattr(props, "title", "") or ""
            album = getattr(props, "album_title", "") or getattr(props, "album", "") or ""
            artist_raw = getattr(props, "artist", "") or getattr(props, "album_artist", "") or ""
            artist, album_hint = _extract_album_from_artist(artist_raw)
            if not album and album_hint:
                album = album_hint

            track_key = f"{app_id}||{title}||{album}||{artist}"
            has_thumb = getattr(props, "thumbnail", None) is not None
            art_sig = f"{track_key}||thumb:{int(has_thumb)}"

            art_available = last_has_art
            if art_sig != last_art_sig:
                out_path = art_dir / ART_FILENAME
                if has_thumb:
                    wrote = await _read_thumbnail_to_file(session, out_path)
                    if not wrote:
                        _write_placeholder(out_path)
                    art_available = wrote
                else:
                    _write_placeholder(out_path)
                    art_available = False
                last_art_sig = art_sig if (title or album or artist) else None
                last_has_art = art_available

            np = NowPlaying(
                title=title,
                album=album,
                artist=artist,
                playing=playing,
                source_app=app_id,
                art_url=f"/art/{ART_FILENAME}",
                has_art=last_has_art,
                updated_unix=int(time.time()),
            )
            await state.set_now_playing(np)
            await state.broadcast({"type": "nowplaying", "data": np.to_dict()})
        except Exception:
            # transient errors: keep last state
            pass

        await asyncio.sleep(1)


