## Streamer Widgets (OBS Browser Sources)

This app runs a **single local web server** that hosts multiple streamer widgets (starting with **Now Playing**) on **one port**, and pushes updates via **WebSockets**.

### Run (dev)

```bash
uv sync
uv run streamer-widgets --tray
```

Then add this as an OBS Browser Source:

- **Now Playing**: `http://127.0.0.1:8765/widgets/nowplaying/`

### Build a standalone `.exe` (PyInstaller)

```bash
uv sync --group build
pyinstaller --noconsole --onefile --name streamer-widgets ^
  --add-data "app/assets/web;app/assets/web" ^
  run_tray.py
```

The executable will be in `dist/streamer-widgets.exe`.


