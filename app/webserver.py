from __future__ import annotations

from pathlib import Path

from aiohttp import WSMsgType, web

from app.paths import get_art_dir, get_web_assets_dir
from app.state import AppState

# Declare widgets once to avoid duplicated slugs/labels.
WIDGETS = [
    {"slug": "nowplaying", "label": "Now Playing"},
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
            
            item_html = f"""
            <li class="widget-item">
              <div class="widget-header">
                <a class="widget-name" href="{url}" target="_blank">{label}</a>
              </div>
              <div class="widget-url-row">{url}</div>
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
    web_root = get_web_assets_dir()
    index_path = web_root / "widgets" / slug / "index.html"
    if index_path.exists():
        return web.FileResponse(path=str(index_path))
    raise web.HTTPNotFound(text="Widget not found")


async def handle_nowplaying(request: web.Request) -> web.Response:
    state: AppState = request.app["state"]
    np = await state.get_now_playing()
    return web.json_response(np.to_dict())


async def handle_ws(request: web.Request) -> web.WebSocketResponse:
    state: AppState = request.app["state"]
    ws = web.WebSocketResponse(heartbeat=30)
    await ws.prepare(request)

    await state.register_ws(ws)
    try:
        # Send initial snapshot
        np = await state.get_now_playing()
        await ws.send_json({"type": "nowplaying", "data": np.to_dict()})

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
    app = web.Application()
    app["state"] = state

    web_root = get_web_assets_dir()
    art_dir = get_art_dir()

    # Pages / API
    app.router.add_get("/", handle_root)
    for widget in WIDGETS:
        slug = widget["slug"]
        app.router.add_get(f"/widgets/{slug}/", handle_widget)
    app.router.add_get("/api/nowplaying", handle_nowplaying)
    app.router.add_get("/ws", handle_ws)

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


