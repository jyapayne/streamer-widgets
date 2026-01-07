from __future__ import annotations

import os


def run_tray_app(host: str = "127.0.0.1", port: int = 8765) -> None:
    """
    Tray entrypoint.

    On Windows, prefer a native pywin32 tray icon (reliable + shows up in Win11 tray settings).
    Fallback to pystray for non-Windows platforms.
    """
    if os.name == "nt":
        from app.win_tray import run_windows_tray

        run_windows_tray(host=host, port=port)
        return

    # Non-Windows fallback (best effort)
    from dataclasses import dataclass
    from typing import Any

    import pyperclip
    import pystray
    from PIL import Image, ImageDraw

    from app.main import ServerController

    @dataclass(frozen=True)
    class TrayConfig:
        host: str = "127.0.0.1"
        port: int = 8765

        def widget_url(self, widget: str) -> str:
            return f"http://{self.host}:{self.port}/widgets/{widget}/"

    cfg = TrayConfig(host=host, port=port)
    server = ServerController(host=host, port=port)
    server.start()

    def _make_icon() -> Image.Image:
        size = 32
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.ellipse((3, 3, size - 4, size - 4), fill=(30, 64, 175, 255))
        d.ellipse((9, 8, 20, 19), fill=(191, 219, 254, 200))
        return img

    def copy_nowplaying(_: Any, __: Any) -> None:
        pyperclip.copy(cfg.widget_url("nowplaying"))

    def start_server(_: Any, __: Any) -> None:
        server.start()

    def stop_server(_: Any, __: Any) -> None:
        server.stop()

    def quit_app(icon: Any, __: Any) -> None:
        try:
            server.stop()
        finally:
            icon.stop()

    icon = pystray.Icon(
        "streamer-widgets",
        _make_icon(),
        title="Streamer Widgets",
        menu=pystray.Menu(
            pystray.MenuItem("Copy Now Playing URL", copy_nowplaying),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Start server", start_server),
            pystray.MenuItem("Stop server", stop_server),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit", quit_app),
        ),
    )
    icon.visible = True
    icon.run()


