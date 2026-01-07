## Streamer Widgets (OBS Browser Sources)

This app runs a **single local web server** that hosts multiple streamer widgets on **one port**, and pushes updates via **WebSockets**.

### Available Widgets

- **Now Playing**: Display currently playing music from Windows Media
- **Live Chat**: Display Twitch and YouTube live chat with emote support (FFZ, BTTV, 7TV)
- **Viewer Count**: Display live viewer count from Twitch and/or YouTube

### Run (dev)

```bash
uv sync
uv run streamer-widgets --tray
```

Then add as OBS Browser Sources:

- **Now Playing**: `http://127.0.0.1:8765/widgets/nowplaying/`
- **Live Chat**: `http://127.0.0.1:8765/widgets/livechat/`
- **Viewer Count**: `http://127.0.0.1:8765/widgets/viewercount/`
- **Configuration**: `http://127.0.0.1:8765/config`

---

## Widget Documentation

### Now Playing Widget

Displays the currently playing song from Windows Media with album art.

**Features:**
- Real-time updates via WebSocket
- Album art display with animated bubble fallback
- Auto-hide when nothing is playing
- Marquee scrolling for long titles
- Playing/Paused status indicator

**OBS Setup:**
- URL: `http://127.0.0.1:8765/widgets/nowplaying/`
- Recommended size: 400×150 px
- Transparent background

**Note:** This widget reads from Windows Media Session (works with Spotify, Windows Media Player, browsers playing media, etc.)

---

### Live Chat Widget

Displays Twitch and YouTube live chat with emote support.

**URL Options:**

| Parameter | Values | Default | Description |
|-----------|--------|---------|-------------|
| `theme` | `dark`, `light` | `dark` | Background style (dark is transparent) |
| `direction` | `down`, `up` | `down` | Message flow direction |
| `fontsize` | `small`, `medium`, `large`, `xlarge` | `medium` | Text and emote size |
| `hidetime` | `true`, `false` | `false` | Hide message timestamps |

**Example URLs:**
```
# Default (dark, scrolls down)
http://127.0.0.1:8765/widgets/livechat/

# Light theme for light backgrounds
http://127.0.0.1:8765/widgets/livechat/?theme=light

# Large font, no timestamps
http://127.0.0.1:8765/widgets/livechat/?fontsize=large&hidetime=true

# Bubbles up (newest at bottom, anchored)
http://127.0.0.1:8765/widgets/livechat/?direction=up
```

**OBS Setup:**
- Recommended size: 400×600 px
- Check "Shutdown source when not visible" for performance

**Emote Support:**
- Twitch native emotes
- FrankerFaceZ (FFZ) - global + channel
- BetterTTV (BTTV) - global + top shared + trending + channel
- 7TV - global + top + trending + channel

See [CHAT_SETUP.md](CHAT_SETUP.md) for OAuth setup instructions.

---

### Viewer Count Widget

The viewer count widget displays your live viewer count from Twitch and/or YouTube.

**URL Options:**

| Parameter | Values | Default | Description |
|-----------|--------|---------|-------------|
| `theme` | `dark`, `light`, `minimal` | `dark` | Widget background style |
| `fontsize` | `small`, `medium`, `large`, `xlarge` | `medium` | Text size |
| `hidelabel` | `true`, `false` | `false` | Hide "viewers" label |
| `livedot` | `true`, `false` | `false` | Show animated red live indicator |
| `interval` | Number (seconds, min 10) | `30` | Refresh interval |

**Example URLs:**
```
# Default
http://127.0.0.1:8765/widgets/viewercount/

# Large with live dot
http://127.0.0.1:8765/widgets/viewercount/?fontsize=large&livedot=true

# Minimal for clean overlay
http://127.0.0.1:8765/widgets/viewercount/?theme=minimal&hidelabel=true

# Compact with fast refresh
http://127.0.0.1:8765/widgets/viewercount/?fontsize=small&interval=15
```

**Note:** The widget uses the Twitch channel and YouTube video ID configured in `/config`. Requires OAuth login for API access.

### Build a standalone `.exe` (PyInstaller)

```bash
uv sync --group build
pyinstaller --noconsole --onefile --name streamer-widgets ^
  --add-data "app/assets/web;app/assets/web" ^
  run_tray.py
```

The executable will be in `dist/streamer-widgets.exe`.

**For end users:** Configuration files are stored in `%LOCALAPPDATA%\StreamerWidgets\`. The app auto-creates a config template on first run. Use the config UI at http://127.0.0.1:8765/config to open the config directory and set up OAuth credentials.


