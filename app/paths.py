from __future__ import annotations

import os
from pathlib import Path


def get_data_dir() -> Path:
    """
    Writable per-user data dir.
    """
    base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA") or str(Path.home())
    return Path(base) / "StreamerWidgets"


def get_art_dir() -> Path:
    d = get_data_dir() / "art"
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_web_assets_dir() -> Path:
    """
    Packaged (read-only) web assets directory.
    """
    return Path(__file__).resolve().parent / "assets" / "web"


