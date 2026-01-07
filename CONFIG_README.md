# Configuration Guide

## OAuth Credentials Configuration

OAuth credentials for Twitch and YouTube are **no longer hardcoded** in the source code. Instead, they are loaded from a JSON configuration file.

### Configuration File Location

The config file is automatically created on first run at:

- **Windows**: `%LOCALAPPDATA%\StreamerWidgets\config.json`
- **Typical path**: `C:\Users\YourName\AppData\Local\StreamerWidgets\config.json`

You can also see the exact path in the web UI at: http://127.0.0.1:8765/config

### Example Configuration

See `config.example.json` in the project root for a template.

```json
{
  "twitch_oauth": {
    "client_id": "YOUR_TWITCH_CLIENT_ID",
    "client_secret": "YOUR_TWITCH_CLIENT_SECRET",
    "redirect_uri": "http://localhost:8765/auth/twitch/callback"
  },
  "youtube_oauth": {
    "client_id": "YOUR_YOUTUBE_CLIENT_ID.apps.googleusercontent.com",
    "client_secret": "YOUR_YOUTUBE_CLIENT_SECRET",
    "redirect_uri": "http://localhost:8765/auth/youtube/callback"
  },
  "server_host": "127.0.0.1",
  "server_port": 8765
}
```

### Setup Steps

1. **Run the application once** to generate the config file
2. **Edit the config file** with your OAuth credentials from Twitch/YouTube developer consoles
3. **Restart the application** to load the new credentials
4. **Visit the config UI** at http://127.0.0.1:8765/config to authenticate

### No Credentials Needed for Twitch Anonymous

Twitch chat can be read **anonymously without OAuth**. You only need Twitch OAuth if you want authenticated access (for rate limit benefits).

YouTube **requires OAuth** to access live chat data.

### Security Notes

- The config file is stored locally on your machine
- Never commit `config.json` to version control
- Keep your Client Secrets private
- The example file `config.example.json` contains placeholder values only

For detailed setup instructions, see [CHAT_SETUP.md](CHAT_SETUP.md)
