from __future__ import annotations

from pathlib import Path

from aiohttp import WSMsgType, web

from app.chat_models import ChatConfig
from app.config import get_config_file, load_config, save_chat_settings
from app.paths import get_art_dir, get_web_assets_dir
from app.state import AppState

# Declare widgets once to avoid duplicated slugs/labels.
WIDGETS = [
    {"slug": "nowplaying", "label": "Now Playing"},
    {"slug": "livechat", "label": "Live Chat"},
    {"slug": "viewercount", "label": "Viewer Count"},
]


async def handle_root(request: web.Request) -> web.Response:
    index_path = get_web_assets_dir() / "index.html"
    if not index_path.exists():
        return web.Response(text="Streamer Widgets: /widgets/nowplaying/", content_type="text/plain")

    try:
        html = index_path.read_text(encoding="utf-8")
        hostport = f"http://{request.host}"
        widget_items = []
        for widget in WIDGETS:
            slug = widget.get("slug", "").strip("/")
            label = widget.get("label", slug or "Widget")
            url = f"http://{request.host}/widgets/{slug}/" if slug else ""
            
            if slug == "livechat":
                # Live Chat widget with options
                item_html = f"""
                <li class="widget-item">
                  <div class="widget-header">
                    <a id="livechat-open" class="widget-name" href="{url}" target="_blank">{label}</a>
                  </div>
                  <div class="widget-url-row">
                    <input type="hidden" id="livechat-base-url" value="{url}">
                    <input type="text" id="livechat-url" value="{url}" readonly>
                    <button class="copy-btn" onclick="copyUrl('livechat-url')">Copy</button>
                  </div>
                  <div class="widget-options">
                    <div class="option-group">
                      <label>Theme</label>
                      <select id="livechat-theme" onchange="updateLiveChatUrl()">
                        <option value="dark">Dark (transparent)</option>
                        <option value="light">Light</option>
                      </select>
                    </div>
                    <div class="option-group">
                      <label>Direction</label>
                      <select id="livechat-direction" onchange="updateLiveChatUrl()">
                        <option value="down">Down (scrolls down)</option>
                        <option value="up">Up (bubbles up, newest anchored)</option>
                      </select>
                    </div>
                    <div class="option-group">
                      <label>Font Size</label>
                      <select id="livechat-fontsize" onchange="updateLiveChatUrl()">
                        <option value="small">Small</option>
                        <option value="medium" selected>Medium</option>
                        <option value="large">Large</option>
                        <option value="xlarge">Extra Large</option>
                      </select>
                    </div>
                    <div class="option-group">
                      <label>Timestamp</label>
                      <select id="livechat-hidetime" onchange="updateLiveChatUrl()">
                        <option value="false">Show</option>
                        <option value="true">Hide</option>
                      </select>
                    </div>
                  </div>
                </li>
                """
            elif slug == "viewercount":
                # Viewer Count widget with options
                item_html = f"""
                <li class="widget-item">
                  <div class="widget-header">
                    <a id="viewercount-open" class="widget-name" href="{url}" target="_blank">{label}</a>
                  </div>
                  <div class="widget-url-row">
                    <input type="hidden" id="viewercount-base-url" value="{url}">
                    <input type="text" id="viewercount-url" value="{url}" readonly>
                    <button class="copy-btn" onclick="copyUrl('viewercount-url')">Copy</button>
                  </div>
                  <div class="widget-options">
                    <div class="option-group">
                      <label>Theme</label>
                      <select id="viewercount-theme" onchange="updateViewerCountUrl()">
                        <option value="dark">Dark</option>
                        <option value="light">Light</option>
                        <option value="minimal">Minimal (no bg)</option>
                      </select>
                    </div>
                    <div class="option-group">
                      <label>Font Size</label>
                      <select id="viewercount-fontsize" onchange="updateViewerCountUrl()">
                        <option value="small">Small</option>
                        <option value="medium" selected>Medium</option>
                        <option value="large">Large</option>
                        <option value="xlarge">Extra Large</option>
                      </select>
                    </div>
                    <div class="option-group">
                      <label>Label</label>
                      <select id="viewercount-hidelabel" onchange="updateViewerCountUrl()">
                        <option value="false">Show</option>
                        <option value="true">Hide</option>
                      </select>
                    </div>
                    <div class="option-group">
                      <label>Live Dot</label>
                      <select id="viewercount-livedot" onchange="updateViewerCountUrl()">
                        <option value="false">Hide</option>
                        <option value="true">Show</option>
                      </select>
                    </div>
                  </div>
                </li>
                """
            else:
                # Standard widget without options
                item_html = f"""
                <li class="widget-item">
                  <div class="widget-header">
                    <a class="widget-name" href="{url}" target="_blank">{label}</a>
                  </div>
                  <div class="widget-url-row">
                    <input type="text" id="{slug}-url" value="{url}" readonly>
                    <button class="copy-btn" onclick="copyUrl('{slug}-url')">Copy</button>
                  </div>
                </li>
                """
            widget_items.append(item_html)
        widget_list_html = "\n".join(widget_items) if widget_items else '<li class="widget-item">No widgets configured</li>'

        # Simple placeholder substitution
        html = (
            html.replace("{{HOSTPORT}}", hostport)
            .replace("{{WIDGET_LIST}}", widget_list_html)
        )
        return web.Response(text=html, content_type="text/html")
    except Exception:
        return web.FileResponse(path=str(index_path))


async def handle_widget(request: web.Request) -> web.FileResponse:
    slug = request.match_info.get("slug")
    if not slug:
        raise web.HTTPNotFound(text="Widget not found")
    web_root = get_web_assets_dir()
    index_path = web_root / "widgets" / slug / "index.html"
    if index_path.exists():
        return web.FileResponse(path=str(index_path))
    raise web.HTTPNotFound(text="Widget not found")


async def handle_nowplaying(request: web.Request) -> web.Response:
    state: AppState = request.app["state"]
    np = await state.get_now_playing()
    return web.json_response(np.to_dict())


async def handle_chat_messages(request: web.Request) -> web.Response:
    """API endpoint to get recent chat messages."""
    state: AppState = request.app["state"]
    limit = int(request.query.get("limit", 50))
    messages = await state.get_chat_messages(limit)
    return web.json_response([msg.to_dict() for msg in messages])


async def handle_chat_config_get(request: web.Request) -> web.Response:
    """Get current chat configuration."""
    state: AppState = request.app["state"]
    config = state.chat_config
    return web.json_response(config.to_dict())


async def handle_chat_config_post(request: web.Request) -> web.Response:
    """Update chat configuration."""
    state: AppState = request.app["state"]
    data = await request.json()

    # Check if channel settings changed (need to restart chat)
    old_config = state.chat_config
    new_twitch_channel = data.get("twitch_channel", "")
    new_youtube_video_id = data.get("youtube_video_id", "")
    
    channel_changed = (
        old_config.twitch_channel != new_twitch_channel or
        old_config.youtube_video_id != new_youtube_video_id
    )

    config = ChatConfig(
        twitch_enabled=data.get("twitch_enabled", False),
        youtube_enabled=data.get("youtube_enabled", False),
        max_messages=data.get("max_messages", 50),
        show_timestamps=data.get("show_timestamps", True),
        show_badges=data.get("show_badges", True),
        show_platform_icons=data.get("show_platform_icons", True),
        unified_view=data.get("unified_view", True),
        enable_ffz=data.get("enable_ffz", True),
        enable_bttv=data.get("enable_bttv", True),
        enable_7tv=data.get("enable_7tv", True),
        filter_by_roles=data.get("filter_by_roles", []),
        blocked_keywords=data.get("blocked_keywords", []),
        min_message_length=data.get("min_message_length", 0),
        twitch_channel=new_twitch_channel,
        youtube_video_id=new_youtube_video_id,
    )

    await state.update_chat_config(config)

    # Save chat settings to disk for persistence
    save_chat_settings({
        "twitch_channel": config.twitch_channel,
        "youtube_video_id": config.youtube_video_id,
        "max_messages": config.max_messages,
        "show_timestamps": config.show_timestamps,
        "show_badges": config.show_badges,
        "show_platform_icons": config.show_platform_icons,
        "unified_view": config.unified_view,
        "enable_ffz": config.enable_ffz,
        "enable_bttv": config.enable_bttv,
        "enable_7tv": config.enable_7tv,
    })

    # Restart chat connections if channel settings changed
    if channel_changed and state.chat_manager:
        await state.chat_manager.restart()

    return web.json_response({"status": "ok"})


async def handle_config_page(request: web.Request) -> web.FileResponse:
    """Serve the configuration page."""
    config_path = get_web_assets_dir() / "config.html"
    return web.FileResponse(path=str(config_path))


async def handle_oauth_status(request: web.Request) -> web.Response:
    """Get OAuth configuration status."""
    app_config = load_config()

    return web.json_response({
        "twitch_configured": app_config.twitch_oauth.is_configured(),
        "youtube_configured": app_config.youtube_oauth.is_configured(),
        "config_file": str(get_config_file()),
    })


async def handle_auth_status(request: web.Request) -> web.Response:
    """Get authentication status (whether user has logged in)."""
    from app.chat_models import Platform

    state: AppState = request.app["state"]
    
    twitch_tokens = await state.get_auth_tokens(Platform.TWITCH)
    youtube_tokens = await state.get_auth_tokens(Platform.YOUTUBE)

    return web.json_response({
        "twitch_authenticated": twitch_tokens is not None and not twitch_tokens.is_expired(),
        "youtube_authenticated": youtube_tokens is not None and not youtube_tokens.is_expired(),
    })


async def handle_open_config_dir(request: web.Request) -> web.Response:
    """Open the config directory in file explorer."""
    from app.config import open_config_directory

    success = open_config_directory()

    if success:
        return web.json_response({"status": "ok", "message": "Opened config directory"})
    else:
        return web.json_response(
            {"status": "error", "message": "Failed to open directory"},
            status=500
        )


async def handle_viewer_count(request: web.Request) -> web.Response:
    """Get viewer count from Twitch and/or YouTube."""
    import aiohttp
    from app.chat_models import Platform

    state: AppState = request.app["state"]
    app_config = load_config()
    chat_config = state.chat_config

    twitch_count: int | None = None
    youtube_count: int | None = None

    # Fetch Twitch viewer count
    if chat_config.twitch_channel:
        try:
            twitch_tokens = await state.get_auth_tokens(Platform.TWITCH)
            if twitch_tokens and app_config.twitch_oauth.client_id:
                headers = {
                    "Client-ID": app_config.twitch_oauth.client_id,
                    "Authorization": f"Bearer {twitch_tokens.access_token}",
                }
                async with aiohttp.ClientSession() as session:
                    url = f"https://api.twitch.tv/helix/streams?user_login={chat_config.twitch_channel}"
                    async with session.get(url, headers=headers) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            streams = data.get("data", [])
                            if streams:
                                twitch_count = streams[0].get("viewer_count", 0)
                            else:
                                # Channel configured but not live
                                twitch_count = 0
        except Exception as e:
            print(f"Error fetching Twitch viewer count: {e}")

    # Fetch YouTube viewer count
    if chat_config.youtube_video_id:
        try:
            youtube_tokens = await state.get_auth_tokens(Platform.YOUTUBE)
            if youtube_tokens:
                async with aiohttp.ClientSession() as session:
                    url = (
                        f"https://www.googleapis.com/youtube/v3/videos"
                        f"?part=liveStreamingDetails&id={chat_config.youtube_video_id}"
                    )
                    headers = {"Authorization": f"Bearer {youtube_tokens.access_token}"}
                    async with session.get(url, headers=headers) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            items = data.get("items", [])
                            if items:
                                live_details = items[0].get("liveStreamingDetails", {})
                                concurrent = live_details.get("concurrentViewers")
                                if concurrent is not None:
                                    youtube_count = int(concurrent)
                                else:
                                    # Video exists but not live
                                    youtube_count = 0
        except Exception as e:
            print(f"Error fetching YouTube viewer count: {e}")

    # Calculate total
    total = 0
    if twitch_count is not None:
        total += twitch_count
    if youtube_count is not None:
        total += youtube_count

    return web.json_response({
        "twitch": twitch_count,
        "youtube": youtube_count,
        "total": total,
    })


async def handle_ws(request: web.Request) -> web.WebSocketResponse:
    state: AppState = request.app["state"]
    ws = web.WebSocketResponse(heartbeat=30)
    await ws.prepare(request)

    await state.register_ws(ws)
    try:
        # Send initial snapshots
        np = await state.get_now_playing()
        await ws.send_json({"type": "nowplaying", "data": np.to_dict()})

        # Send chat history
        chat_messages = await state.get_chat_messages(50)
        await ws.send_json({
            "type": "chat_history",
            "data": [msg.to_dict() for msg in chat_messages]
        })

        async for msg in ws:
            if msg.type == WSMsgType.TEXT:
                # Currently no client->server messages required
                pass
            elif msg.type == WSMsgType.ERROR:
                break
    finally:
        await state.unregister_ws(ws)

    return ws


def make_app(state: AppState) -> web.Application:
    from app.auth import register_auth_routes

    app = web.Application()
    app["state"] = state

    web_root = get_web_assets_dir()
    art_dir = get_art_dir()

    # Pages / API
    app.router.add_get("/", handle_root)
    app.router.add_get("/config", handle_config_page)
    app.router.add_get("/widgets/{slug}/", handle_widget)
    app.router.add_get("/api/nowplaying", handle_nowplaying)
    app.router.add_get("/api/chat/messages", handle_chat_messages)
    app.router.add_get("/api/chat/config", handle_chat_config_get)
    app.router.add_post("/api/chat/config", handle_chat_config_post)
    app.router.add_get("/api/oauth/status", handle_oauth_status)
    app.router.add_get("/api/auth/status", handle_auth_status)
    app.router.add_post("/api/config/open-directory", handle_open_config_dir)
    app.router.add_get("/api/viewercount", handle_viewer_count)
    app.router.add_get("/ws", handle_ws)

    # Register OAuth routes
    register_auth_routes(app)

    # Widget static routing
    # e.g. /widgets/nowplaying/ -> web/widgets/nowplaying/index.html
    app.router.add_static(
        "/widgets/",
        path=str(web_root / "widgets"),
        show_index=False,
    )

    # Art assets
    app.router.add_static("/art/", path=str(art_dir))

    return app


