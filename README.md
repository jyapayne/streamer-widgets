## Streamer Widgets (OBS Browser Sources)

This app runs a **single local web server** that hosts multiple streamer widgets on **one port**, and pushes updates via **WebSockets**.

### Available Widgets

- **Now Playing**: Display currently playing music from Windows Media
- **Live Chat**: Display Twitch and YouTube live chat with emote support (FFZ, BTTV, 7TV)

### Run (dev)

```bash
uv sync
uv run streamer-widgets --tray
```

Then add as OBS Browser Sources:

- **Now Playing**: `http://127.0.0.1:8765/widgets/nowplaying/`
- **Live Chat**: `http://127.0.0.1:8765/widgets/livechat/`
- **Configuration**: `http://127.0.0.1:8765/config`

### Live Chat Setup

See [CHAT_SETUP.md](CHAT_SETUP.md) for detailed instructions on:
- Connecting to Twitch and YouTube
- Setting up OAuth authentication
- Configuring emote providers (FFZ, BTTV, 7TV)
- Customizing the chat widget

### Build a standalone `.exe` (PyInstaller)

```bash
uv sync --group build
pyinstaller --noconsole --onefile --name streamer-widgets ^
  --add-data "app/assets/web;app/assets/web" ^
  run_tray.py
```

The executable will be in `dist/streamer-widgets.exe`.

**For end users:** Configuration files are stored in `%LOCALAPPDATA%\StreamerWidgets\`. The app auto-creates a config template on first run. Use the config UI at http://127.0.0.1:8765/config to open the config directory and set up OAuth credentials.


