from __future__ import annotations

import json
import secrets
import webbrowser
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from urllib.parse import urlencode

from aiohttp import web

from app.chat_models import AuthTokens, Platform
from app.config import load_config
from app.paths import get_data_dir
from app.state import AppState

# In-memory state storage for OAuth flow
oauth_states: dict[str, dict] = {}

# Global config - loaded at module level
_app_config = load_config()


def get_tokens_file() -> Path:
    """Get path to tokens storage file."""
    data_dir = get_data_dir()
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / "tokens.json"


async def load_tokens(state: AppState) -> None:
    """Load saved tokens from disk."""
    tokens_file = get_tokens_file()
    if not tokens_file.exists():
        return

    try:
        with open(tokens_file, "r") as f:
            data = json.load(f)

        if "twitch" in data:
            twitch_data = data["twitch"]
            tokens = AuthTokens(
                access_token=twitch_data["access_token"],
                refresh_token=twitch_data.get("refresh_token"),
                expires_at=(
                    datetime.fromisoformat(twitch_data["expires_at"])
                    if twitch_data.get("expires_at")
                    else None
                ),
                scope=twitch_data.get("scope", []),
            )
            await state.set_auth_tokens(Platform.TWITCH, tokens)

        if "youtube" in data:
            youtube_data = data["youtube"]
            tokens = AuthTokens(
                access_token=youtube_data["access_token"],
                refresh_token=youtube_data.get("refresh_token"),
                expires_at=(
                    datetime.fromisoformat(youtube_data["expires_at"])
                    if youtube_data.get("expires_at")
                    else None
                ),
                scope=youtube_data.get("scope", []),
            )
            await state.set_auth_tokens(Platform.YOUTUBE, tokens)

    except Exception as e:
        print(f"Error loading tokens: {e}")


async def save_tokens(state: AppState) -> None:
    """Save tokens to disk."""
    tokens_file = get_tokens_file()

    data = {}

    twitch_tokens = await state.get_auth_tokens(Platform.TWITCH)
    if twitch_tokens:
        data["twitch"] = twitch_tokens.to_dict()

    youtube_tokens = await state.get_auth_tokens(Platform.YOUTUBE)
    if youtube_tokens:
        data["youtube"] = youtube_tokens.to_dict()

    try:
        with open(tokens_file, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Error saving tokens: {e}")


async def handle_twitch_login(request: web.Request) -> web.Response:
    """Initiate Twitch OAuth flow."""
    if not _app_config.twitch_oauth.is_configured():
        return web.json_response(
            {
                "error": "Twitch OAuth not configured. Please edit config.json with your OAuth credentials.",
                "config_path": str(load_config().twitch_oauth),
            },
            status=400,
        )

    state_token = secrets.token_urlsafe(32)
    oauth_states[state_token] = {"platform": "twitch", "timestamp": datetime.now()}

    params = {
        "client_id": _app_config.twitch_oauth.client_id,
        "redirect_uri": _app_config.twitch_oauth.redirect_uri,
        "response_type": "code",
        "scope": "chat:read",
        "state": state_token,
    }

    auth_url = f"https://id.twitch.tv/oauth2/authorize?{urlencode(params)}"

    # Open browser
    webbrowser.open(auth_url)

    return web.json_response({"message": "Opening browser for Twitch login..."})


async def handle_twitch_callback(request: web.Request) -> web.Response:
    """Handle Twitch OAuth callback."""
    code = request.query.get("code")
    state_token = request.query.get("state")

    if not code or not state_token or state_token not in oauth_states:
        return web.Response(text="Invalid OAuth state", status=400)

    del oauth_states[state_token]

    # Exchange code for token
    import aiohttp

    async with aiohttp.ClientSession() as session:
        token_url = "https://id.twitch.tv/oauth2/token"
        data = {
            "client_id": _app_config.twitch_oauth.client_id,
            "client_secret": _app_config.twitch_oauth.client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": _app_config.twitch_oauth.redirect_uri,
        }

        async with session.post(token_url, data=data) as resp:
            if resp.status != 200:
                return web.Response(text="Failed to get access token", status=400)

            token_data = await resp.json()

    # Store tokens
    state: AppState = request.app["state"]
    expires_in = token_data.get("expires_in", 3600)
    tokens = AuthTokens(
        access_token=token_data["access_token"],
        refresh_token=token_data.get("refresh_token"),
        expires_at=datetime.now() + timedelta(seconds=expires_in),
        scope=token_data.get("scope", []),
    )

    await state.set_auth_tokens(Platform.TWITCH, tokens)
    await save_tokens(state)

    html = """<!DOCTYPE html>
<html>
<head>
    <title>Twitch Login Successful</title>
    <style>
        body { font-family: -apple-system, system-ui, sans-serif; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; background: #0f172a; color: white; }
        .card { text-align: center; padding: 40px; background: #1e293b; border-radius: 12px; }
        h1 { color: #a78bfa; margin-bottom: 16px; }
        p { color: #94a3b8; }
    </style>
</head>
<body>
    <div class="card">
        <h1>✓ Twitch Login Successful!</h1>
        <p>This window will close automatically...</p>
        <script>
            if (window.opener && !window.opener.closed) {
                window.opener.onAuthComplete && window.opener.onAuthComplete('twitch');
            }
            setTimeout(() => window.close(), 1500);
        </script>
    </div>
</body>
</html>"""
    return web.Response(text=html, content_type="text/html")


async def handle_youtube_login(request: web.Request) -> web.Response:
    """Initiate YouTube OAuth flow."""
    if not _app_config.youtube_oauth.is_configured():
        return web.json_response(
            {
                "error": "YouTube OAuth not configured. Please edit config.json with your OAuth credentials.",
                "config_path": str(load_config().youtube_oauth),
            },
            status=400,
        )

    state_token = secrets.token_urlsafe(32)
    oauth_states[state_token] = {"platform": "youtube", "timestamp": datetime.now()}

    params = {
        "client_id": _app_config.youtube_oauth.client_id,
        "redirect_uri": _app_config.youtube_oauth.redirect_uri,
        "response_type": "code",
        "scope": "https://www.googleapis.com/auth/youtube.readonly",
        "state": state_token,
        "access_type": "offline",
        "prompt": "consent",
    }

    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"

    webbrowser.open(auth_url)

    return web.json_response({"message": "Opening browser for YouTube login..."})


async def handle_youtube_callback(request: web.Request) -> web.Response:
    """Handle YouTube OAuth callback."""
    code = request.query.get("code")
    state_token = request.query.get("state")

    if not code or not state_token or state_token not in oauth_states:
        return web.Response(text="Invalid OAuth state", status=400)

    del oauth_states[state_token]

    # Exchange code for token
    import aiohttp

    async with aiohttp.ClientSession() as session:
        token_url = "https://oauth2.googleapis.com/token"
        data = {
            "client_id": _app_config.youtube_oauth.client_id,
            "client_secret": _app_config.youtube_oauth.client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": _app_config.youtube_oauth.redirect_uri,
        }

        async with session.post(token_url, data=data) as resp:
            if resp.status != 200:
                return web.Response(text="Failed to get access token", status=400)

            token_data = await resp.json()

    # Store tokens
    state: AppState = request.app["state"]
    expires_in = token_data.get("expires_in", 3600)
    tokens = AuthTokens(
        access_token=token_data["access_token"],
        refresh_token=token_data.get("refresh_token"),
        expires_at=datetime.now() + timedelta(seconds=expires_in),
        scope=token_data.get("scope", "").split(),
    )

    await state.set_auth_tokens(Platform.YOUTUBE, tokens)
    await save_tokens(state)

    html = """<!DOCTYPE html>
<html>
<head>
    <title>YouTube Login Successful</title>
    <style>
        body { font-family: -apple-system, system-ui, sans-serif; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; background: #0f172a; color: white; }
        .card { text-align: center; padding: 40px; background: #1e293b; border-radius: 12px; }
        h1 { color: #f87171; margin-bottom: 16px; }
        p { color: #94a3b8; }
    </style>
</head>
<body>
    <div class="card">
        <h1>✓ YouTube Login Successful!</h1>
        <p>This window will close automatically...</p>
        <script>
            if (window.opener && !window.opener.closed) {
                window.opener.onAuthComplete && window.opener.onAuthComplete('youtube');
            }
            setTimeout(() => window.close(), 1500);
        </script>
    </div>
</body>
</html>"""
    return web.Response(text=html, content_type="text/html")


def register_auth_routes(app: web.Application) -> None:
    """Register OAuth routes to the application."""
    app.router.add_get("/auth/twitch/login", handle_twitch_login)
    app.router.add_get("/auth/twitch/callback", handle_twitch_callback)
    app.router.add_get("/auth/youtube/login", handle_youtube_login)
    app.router.add_get("/auth/youtube/callback", handle_youtube_callback)
