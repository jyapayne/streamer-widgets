# Distribution Guide

## How the Config System Works with PyInstaller

### Architecture Overview

The application uses a **two-location** file system:

1. **Bundled Files (Read-Only)** - Inside the .exe
   - Python source code
   - Web assets (`app/assets/web/`)
   - Everything compiled into the executable

2. **User Data Directory (Read-Write)** - User's local machine
   - Configuration: `%LOCALAPPDATA%\StreamerWidgets\config.json`
   - OAuth Tokens: `%LOCALAPPDATA%\StreamerWidgets\tokens.json`
   - Album Art: `%LOCALAPPDATA%\StreamerWidgets\art\`

### Why This Works Well

**Benefits:**
- ✅ **No hardcoded credentials** in the .exe
- ✅ **Survives updates** - User config persists when you release new versions
- ✅ **User-specific** - Each user has their own OAuth credentials
- ✅ **Secure** - Credentials never in source control or distributed executable
- ✅ **Easy to find** - Standard Windows application data location

**User Experience:**
1. User downloads and runs `streamer-widgets.exe`
2. App creates `config.json` automatically on first run
3. User visits http://127.0.0.1:8765/config
4. Clicks "Open Config Directory" button
5. Edits `config.json` with their OAuth credentials
6. Restarts the app
7. OAuth authentication works!

## Building the Executable

### Build Command

```bash
uv sync --group build
pyinstaller --noconsole --onefile --name streamer-widgets ^
  --add-data "app/assets/web;app/assets/web" ^
  run_tray.py
```

### What Gets Bundled

- All Python code
- `app/assets/web/` directory (HTML, CSS, JS for widgets)
- Python dependencies

### What Does NOT Get Bundled

- `config.json` - Created at runtime in user directory
- `tokens.json` - Created when user authenticates
- `config.example.json` - Template file (not needed in .exe)

## Distribution Checklist

When distributing the application:

- [ ] Build the executable with PyInstaller
- [ ] Test the .exe on a clean machine (no Python installed)
- [ ] Verify config directory creation works
- [ ] Test "Open Config Directory" button in web UI
- [ ] Include `CHAT_SETUP.md` or link to documentation
- [ ] Provide example OAuth setup instructions

## User Setup Instructions (for README/docs)

### For End Users

**First Run:**

1. Run `streamer-widgets.exe`
2. The app creates a configuration file automatically
3. Open http://127.0.0.1:8765/config in your browser

**Setting Up Chat Authentication:**

1. In the config UI, you'll see a warning if OAuth is not configured
2. Click the **"📁 Open Config Directory"** button
3. This opens: `C:\Users\YourName\AppData\Local\StreamerWidgets\`
4. Edit `config.json` with your OAuth credentials:
   - Get Twitch credentials from https://dev.twitch.tv/console/apps
   - Get YouTube credentials from https://console.cloud.google.com/
5. Save the file
6. **Restart the application**
7. Return to http://127.0.0.1:8765/config and click "Login with Twitch/YouTube"

**Example config.json:**

```json
{
  "twitch_oauth": {
    "client_id": "your_twitch_client_id_here",
    "client_secret": "your_twitch_client_secret_here",
    "redirect_uri": "http://localhost:8765/auth/twitch/callback"
  },
  "youtube_oauth": {
    "client_id": "your_youtube_client_id.apps.googleusercontent.com",
    "client_secret": "your_youtube_client_secret_here",
    "redirect_uri": "http://localhost:8765/auth/youtube/callback"
  },
  "server_host": "127.0.0.1",
  "server_port": 8765
}
```

## Troubleshooting for Users

### "I can't find the config file"

1. Visit http://127.0.0.1:8765/config
2. The warning box shows the exact path
3. Or click "Open Config Directory" to open it directly

### "OAuth isn't working"

1. Check that `client_id` and `client_secret` are filled in (not placeholders)
2. Make sure you **restarted the app** after editing config.json
3. Verify the redirect URIs match in both:
   - Your Twitch/YouTube developer console
   - The `config.json` file

### "Config directory won't open"

The path is always: `%LOCALAPPDATA%\StreamerWidgets\`

In Windows:
1. Press `Win + R`
2. Type: `%LOCALAPPDATA%\StreamerWidgets`
3. Press Enter

## Updates and Versioning

When you release a new version:

1. Users download the new `.exe`
2. **Config persists** - No need to reconfigure OAuth
3. **Tokens persist** - Users stay authenticated
4. Just replace the old .exe with the new one

The config directory is **separate from the executable**, so updates are seamless.

## Security Considerations

**What's Safe:**
- Distribute `streamer-widgets.exe` publicly
- Share the source code on GitHub
- Include `config.example.json` as a template

**What to NEVER Distribute:**
- Actual `config.json` with real credentials
- `tokens.json` files
- Real OAuth Client IDs/Secrets

**User Responsibility:**
- Users must obtain their own OAuth credentials
- Credentials are stored locally on their machine only
- Never share `config.json` or `tokens.json` files

## Advantages Over Alternatives

### Why Not Environment Variables?
❌ Hard for non-technical users
❌ Doesn't work well with PyInstaller .exe
❌ Difficult to edit and manage

### Why Not Hardcoded Credentials?
❌ Security risk
❌ Every user would use the same credentials
❌ Would hit OAuth rate limits
❌ Can't distribute publicly

### Why Config File in User Directory?
✅ Standard practice for desktop apps
✅ Survives application updates
✅ User-specific credentials
✅ Easy to locate and edit
✅ Secure (local machine only)
✅ Works perfectly with PyInstaller

## Summary

The config system is **production-ready for distribution**:

1. **No code changes needed** by end users
2. **Auto-creates config** on first run
3. **Easy to find** via UI button
4. **Persists across updates**
5. **Secure** - no credentials in .exe
6. **User-friendly** - clear instructions in UI

Just build the .exe and distribute it. Users will be guided through the setup process by the web UI.
