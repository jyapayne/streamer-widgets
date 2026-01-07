# Live Chat Widget Setup Guide

This guide will help you set up the Live Chat widget to display Twitch and YouTube live chat in OBS.

## Quick Start

1. **Start the server**
   ```bash
   uv run streamer-widgets --tray
   ```

2. **Configure Chat**
   - Open http://127.0.0.1:8765/config in your browser
   - Configure your Twitch channel and/or YouTube video ID
   - (Optional) Set up OAuth for authenticated connections

3. **Add to OBS**
   - Create a new Browser Source
   - URL: `http://127.0.0.1:8765/widgets/livechat/`
   - Width: 400px (or your preference)
   - Height: 600px (or your preference)
   - Check "Shutdown source when not visible" for performance

## Features

### Supported Platforms
- **Twitch**: IRC WebSocket connection (anonymous or authenticated)
- **YouTube**: Live Chat API (requires OAuth)

### Emote Support
- Twitch native emotes
- FrankerFaceZ (FFZ)
- BetterTTV (BTTV)
- 7TV
- YouTube emoji (native)

### Display Options
- **Unified View**: Mix messages from both platforms chronologically
- **Separate Columns**: (Coming soon) Side-by-side platform displays
- Customizable message limit
- Timestamps
- User badges
- Platform indicators

## Authentication Setup

### Configuration File

OAuth credentials are stored in a JSON configuration file. On first run, the application creates an example config at:

**Windows:** `%LOCALAPPDATA%\StreamerWidgets\config.json`

You can also find the exact path in the web UI at http://127.0.0.1:8765/config

### Twitch OAuth (Optional)

For anonymous chat reading, you don't need OAuth. For authenticated connections:

1. **Create a Twitch Application**
   - Go to https://dev.twitch.tv/console/apps
   - Click "Register Your Application"
   - Name: `My Chat Widget` (or any name)
   - OAuth Redirect URLs: `http://localhost:8765/auth/twitch/callback`
   - Category: Chat Bot
   - Client Type: **Confidential**
   - Click "Create"

2. **Configure Credentials**
   - Open `config.json` in a text editor (see path above)
   - Under `twitch_oauth`, set:
     - `client_id`: Your Twitch Client ID
     - `client_secret`: Your Twitch Client Secret
     - `redirect_uri`: Keep as `http://localhost:8765/auth/twitch/callback`
   - Save the file
   - **Restart the application**

   Example:
   ```json
   {
     "twitch_oauth": {
       "client_id": "abc123xyz456",
       "client_secret": "def789ghi012",
       "redirect_uri": "http://localhost:8765/auth/twitch/callback"
     }
   }
   ```

3. **Authenticate**
   - Go to http://127.0.0.1:8765/config
   - Click "Login with Twitch"
   - Authorize the application in the browser popup

### YouTube OAuth (Required for YouTube)

YouTube Live Chat requires OAuth authentication:

1. **Create a Google Cloud Project**
   - Go to https://console.cloud.google.com/
   - Create a new project
   - Enable "YouTube Data API v3"

2. **Create OAuth Credentials**
   - Go to "Credentials" in your project
   - Click "Create Credentials" → "OAuth client ID"
   - Application type: Web application
   - Authorized redirect URIs: `http://localhost:8765/auth/youtube/callback`
   - Click "Create"

3. **Configure Credentials**
   - Open `config.json` in a text editor
   - Under `youtube_oauth`, set:
     - `client_id`: Your YouTube Client ID (ends with `.apps.googleusercontent.com`)
     - `client_secret`: Your YouTube Client Secret
     - `redirect_uri`: Keep as `http://localhost:8765/auth/youtube/callback`
   - Save the file
   - **Restart the application**

   Example:
   ```json
   {
     "youtube_oauth": {
       "client_id": "123456789-abc.apps.googleusercontent.com",
       "client_secret": "GOCSPX-xyz123abc456",
       "redirect_uri": "http://localhost:8765/auth/youtube/callback"
     }
   }
   ```

4. **Authenticate**
   - Go to http://127.0.0.1:8765/config
   - Click "Login with YouTube"
   - Sign in with your Google account
   - Authorize the application

## Configuration Options

### Channel/Video Settings
- **Twitch Channel**: The channel name to monitor (without #)
- **YouTube Video ID**: The ID from the YouTube video/stream URL
  - Example: For `https://youtube.com/watch?v=dQw4w9WgXcQ`, use `dQw4w9WgXcQ`

### Emote Providers
- Enable/disable FFZ, BTTV, and 7TV emotes
- Emotes are loaded when connecting to a channel

### Display Settings
- **Max Messages**: Number of messages to keep (10-200)
- **Show Timestamps**: Display message times
- **Show Badges**: Display user badges (mod, subscriber, etc.)
- **Unified View**: Mix both platforms or show separately

### Filtering (Advanced)
Not yet implemented in UI, but available via API:
- Filter by user roles
- Block messages with specific keywords
- Set minimum message length

## Customization

### Widget Styling

Edit `app/assets/web/widgets/livechat/style.css` to customize:
- Colors and themes
- Font sizes
- Message spacing
- Platform indicators
- Badge styles

### Widget Size

Adjust in OBS Browser Source properties:
- **Vertical chat**: 400x600px or 400x800px
- **Horizontal chat**: 800x400px or 1000x400px

## Troubleshooting

### Twitch Chat Not Connecting
- Check that the channel name is correct (lowercase, no #)
- For authenticated connections, verify OAuth tokens are valid
- Check console output for error messages

### YouTube Chat Not Showing
- Ensure the video/stream has live chat enabled
- Verify OAuth authentication is complete
- Check that the video ID is correct
- YouTube requires authenticated access

### Emotes Not Loading
- Check internet connection
- Third-party emote services may be rate-limited
- Try disabling/re-enabling emote providers in config

### Messages Not Appearing in OBS
- Verify the widget URL is correct
- Check that the browser source is visible
- Refresh the browser source
- Check browser console for WebSocket errors

## API Endpoints

For advanced integration:

- `GET /api/chat/messages?limit=50` - Get recent messages
- `GET /api/chat/config` - Get current configuration
- `POST /api/chat/config` - Update configuration
- `GET /ws` - WebSocket for real-time updates

## Notes

- Tokens are stored locally in `%LOCALAPPDATA%/StreamerWidgets/tokens.json`
- Chat history is kept in memory (not persisted)
- Anonymous Twitch connections have no rate limits for reading
- YouTube API has daily quotas (should be sufficient for chat reading)

## Future Enhancements

- [ ] Chat commands/interactions
- [ ] Message filtering UI
- [ ] Custom badge images
- [ ] Sound notifications
- [ ] Chat replay/history
- [ ] Multi-column layout
- [ ] Custom CSS themes
- [ ] Raid/host notifications
- [ ] Viewer count display
