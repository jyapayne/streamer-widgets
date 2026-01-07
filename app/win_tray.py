from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from typing import Any

import pyperclip

from app.main import ServerController
from app.paths import get_data_dir


@dataclass(frozen=True)
class TrayConfig:
    host: str = "127.0.0.1"
    port: int = 8765

    def widget_url(self, widget: str) -> str:
        return f"http://{self.host}:{self.port}/widgets/{widget}/"


def run_windows_tray(host: str = "127.0.0.1", port: int = 8765) -> None:
    """
    Native Windows tray icon using pywin32 (more reliable than pystray on some Win11 setups).
    """
    # Import inside function so non-Windows platforms can still import the module tree.
    import win32api
    import win32con
    import win32gui

    cfg = TrayConfig(host=host, port=port)
    server = ServerController(host=host, port=port)
    server.start()
    status = {"running": True}

    WM_TRAYICON = win32con.WM_USER + 20
    TASKBAR_CREATED = win32gui.RegisterWindowMessage("TaskbarCreated")

    ID_COPY = 1000
    ID_START = 1001
    ID_STOP = 1002
    ID_QUIT = 1099

    class_name = "StreamerWidgetsTray"
    nid_id = 0

    def _ensure_menu_bitmaps() -> dict[int, str]:
        """
        Create small BMPs for menu item icons and return a mapping of command id -> bmp path.
        We use BMPs because Win32 menu item bitmaps are HBITMAP-based.
        """
        from PIL import Image, ImageDraw, ImageFont

        base = get_data_dir() / "menu_icons"
        base.mkdir(parents=True, exist_ok=True)
        version_file = base / "_version.txt"
        icon_set_version = "shape-v2"

        try:
            existing = version_file.read_text(encoding="utf-8").strip()
        except Exception:
            existing = ""

        # If the icon set changed, clear old cached BMPs so new ones render.
        if existing != icon_set_version:
            try:
                shutil.rmtree(base)
            except Exception:
                pass
            base.mkdir(parents=True, exist_ok=True)
            try:
                version_file.write_text(icon_set_version, encoding="utf-8")
            except Exception:
                pass

        def save_icon(name: str, draw_fn) -> str:
            path = base / f"{name}.bmp"
            if path.exists():
                return str(path)
            # 32x32 for decent high-DPI scaling; Win32 downscales reasonably well.
            img = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
            d = ImageDraw.Draw(img)
            draw_fn(d)
            
            # Paste onto white background to ensure visibility on standard menus (transparency is iffy with raw BMPs)
            # or keep it simple with 255,255,255 background if transparent doesn't work.
            # Using a solid white background is safest for standard menus.
            final = Image.new("RGB", (32, 32), (255, 255, 255))
            final.paste(img, (0, 0), img)
            final.save(str(path), format="BMP")
            return str(path)

        blue = (56, 189, 248)
        green = (34, 197, 94)
        red = (239, 68, 68)
        slate = (100, 116, 139)

        # Drawing vector-style icons at 32x32
        copy_bmp = save_icon(
            "copy",
            lambda d: (
                # Two overlapping rectangles
                d.rounded_rectangle((10, 10, 24, 26), radius=3, outline=blue, width=2),
                d.rounded_rectangle((6, 6, 20, 22), radius=3, fill=(255, 255, 255), outline=blue, width=2),
            ),
        )
        start_bmp = save_icon(
            "start",
            lambda d: d.polygon([(10, 6), (24, 16), (10, 26)], fill=green),
        )
        stop_bmp = save_icon(
            "stop",
            lambda d: d.rounded_rectangle((8, 8, 24, 24), radius=2, fill=red),
        )
        quit_bmp = save_icon(
            "quit",
            lambda d: (
                d.line((8, 8, 24, 24), fill=slate, width=3),
                d.line((24, 8, 8, 24), fill=slate, width=3),
            ),
        )

        return {
            ID_COPY: copy_bmp,
            ID_START: start_bmp,
            ID_STOP: stop_bmp,
            ID_QUIT: quit_bmp,
        }

        return {
            ID_COPY: copy_bmp,
            ID_START: start_bmp,
            ID_STOP: stop_bmp,
            ID_QUIT: quit_bmp,
        }

    def _ensure_tray_ico_path(running: bool) -> str:
        """
        Create a small custom .ico on disk so pywin32 can load it reliably.
        """
        from PIL import Image, ImageDraw

        data_dir = get_data_dir()
        data_dir.mkdir(parents=True, exist_ok=True)
        ico_path = data_dir / ("tray_running.ico" if running else "tray_stopped.ico")
        if ico_path.exists():
            return str(ico_path)

        def bubble(size: int) -> Image.Image:
            img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
            d = ImageDraw.Draw(img)
            # dark rounded background for visibility in the tray
            r = max(2, size // 6)
            d.rounded_rectangle((1, 1, size - 2, size - 2), radius=r, fill=(15, 23, 42, 255))
            pad = max(2, size // 8)
            d.ellipse((pad, pad, size - pad - 1, size - pad - 1), fill=(30, 64, 175, 255))
            # highlights
            d.ellipse((size * 0.30, size * 0.26, size * 0.62, size * 0.58), fill=(191, 219, 254, 210))
            d.ellipse((size * 0.64, size * 0.60, size * 0.86, size * 0.82), fill=(56, 189, 248, 235))

            # status dot (bottom-right)
            dot_r = max(3, size // 10)
            cx = int(size * 0.78)
            cy = int(size * 0.78)
            dot_color = (34, 197, 94, 255) if running else (148, 163, 184, 255)
            ring = (15, 23, 42, 255)
            d.ellipse((cx - dot_r - 2, cy - dot_r - 2, cx + dot_r + 2, cy + dot_r + 2), fill=ring)
            d.ellipse((cx - dot_r, cy - dot_r, cx + dot_r, cy + dot_r), fill=dot_color)
            return img

        img = bubble(64)
        # Multi-size ICO for crisp rendering at different DPI/scale.
        img.save(str(ico_path), format="ICO", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64)])
        return str(ico_path)

    def make_hicon() -> int:
        try:
            ico_path = _ensure_tray_ico_path(running=True)
            return win32gui.LoadImage(
                0,
                ico_path,
                win32con.IMAGE_ICON,
                0,
                0,
                win32con.LR_LOADFROMFILE | win32con.LR_DEFAULTSIZE,
            )
        except Exception:
            return win32gui.LoadIcon(0, win32con.IDI_APPLICATION)

    def _load_hicon_for_status(running: bool) -> int:
        try:
            ico_path = _ensure_tray_ico_path(running)
            return win32gui.LoadImage(
                0,
                ico_path,
                win32con.IMAGE_ICON,
                0,
                0,
                win32con.LR_LOADFROMFILE | win32con.LR_DEFAULTSIZE,
            )
        except Exception:
            return win32gui.LoadIcon(0, win32con.IDI_APPLICATION)

    def _tip_for_status(running: bool) -> str:
        return f"Streamer Widgets ({'Running' if running else 'Stopped'}) - {host}:{port}"

    def _modify_icon(hwnd: int, running: bool) -> None:
        hicon = _load_hicon_for_status(running)
        flags = win32gui.NIF_ICON | win32gui.NIF_TIP | win32gui.NIF_MESSAGE
        nid = (hwnd, nid_id, flags, WM_TRAYICON, hicon, _tip_for_status(running))
        win32gui.Shell_NotifyIcon(win32gui.NIM_MODIFY, nid)

    def add_icon(hwnd: int) -> None:
        """
        Add tray icon (tuple-style NOTIFYICONDATA; works across pywin32 versions).
        """
        hicon = make_hicon()
        flags = win32gui.NIF_ICON | win32gui.NIF_MESSAGE | win32gui.NIF_TIP
        tip = _tip_for_status(status["running"])
        nid = (hwnd, nid_id, flags, WM_TRAYICON, hicon, tip)
        win32gui.Shell_NotifyIcon(win32gui.NIM_ADD, nid)

    def remove_icon(hwnd: int) -> None:
        try:
            win32gui.Shell_NotifyIcon(win32gui.NIM_DELETE, (hwnd, nid_id))
        except Exception:
            pass

    def show_menu(hwnd: int) -> None:
        menu = win32gui.CreatePopupMenu()
        win32gui.AppendMenu(menu, win32con.MF_STRING, ID_COPY, "Copy Now Playing URL")
        win32gui.AppendMenu(menu, win32con.MF_SEPARATOR, 0, "")
        win32gui.AppendMenu(menu, win32con.MF_STRING, ID_START, "Start server")
        win32gui.AppendMenu(menu, win32con.MF_STRING, ID_STOP, "Stop server")
        win32gui.AppendMenu(menu, win32con.MF_SEPARATOR, 0, "")
        win32gui.AppendMenu(menu, win32con.MF_STRING, ID_QUIT, "Quit")

        # Attach icons to menu items (best-effort)
        try:
            bmp_map = _ensure_menu_bitmaps()
            for cmd_id, bmp_path in bmp_map.items():
                hbmp = win32gui.LoadImage(
                    0,
                    bmp_path,
                    win32con.IMAGE_BITMAP,
                    0,
                    0,
                    win32con.LR_LOADFROMFILE | win32con.LR_DEFAULTSIZE,
                )
                if hbmp:
                    win32gui.SetMenuItemBitmaps(menu, cmd_id, win32con.MF_BYCOMMAND, hbmp, hbmp)
        except Exception:
            pass

        x, y = win32gui.GetCursorPos()
        win32gui.SetForegroundWindow(hwnd)
        win32gui.TrackPopupMenu(menu, win32con.TPM_LEFTALIGN | win32con.TPM_RIGHTBUTTON, x, y, 0, hwnd, None)
        win32gui.PostMessage(hwnd, win32con.WM_NULL, 0, 0)

    def wndproc(hwnd: int, msg: int, wparam: int, lparam: int) -> int:
        # Always return an int LRESULT.
        if msg == TASKBAR_CREATED:
            add_icon(hwnd)
            _modify_icon(hwnd, status["running"])
            return 0

        if msg == win32con.WM_DESTROY:
            remove_icon(hwnd)
            win32gui.PostQuitMessage(0)
            return 0

        if msg == win32con.WM_COMMAND:
            cmd = win32api.LOWORD(wparam)
            if cmd == ID_COPY:
                pyperclip.copy(cfg.widget_url("nowplaying"))
            elif cmd == ID_START:
                server.start()
                status["running"] = True
                _modify_icon(hwnd, True)
            elif cmd == ID_STOP:
                server.stop()
                status["running"] = False
                _modify_icon(hwnd, False)
            elif cmd == ID_QUIT:
                win32gui.DestroyWindow(hwnd)
            return 0

        if msg == WM_TRAYICON:
            if lparam == win32con.WM_RBUTTONUP:
                show_menu(hwnd)
            elif lparam == win32con.WM_LBUTTONUP:
                pyperclip.copy(cfg.widget_url("nowplaying"))
            return 0

        return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)

    wc = win32gui.WNDCLASS()
    wc.hInstance = win32api.GetModuleHandle(None)
    wc.lpszClassName = class_name
    wc.lpfnWndProc = wndproc
    wc.hIcon = make_hicon()
    try:
        win32gui.RegisterClass(wc)
    except win32gui.error:
        pass

    hwnd = win32gui.CreateWindow(
        class_name,
        "Streamer Widgets",
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        wc.hInstance,
        None,
    )

    add_icon(hwnd)
    try:
        win32gui.PumpMessages()
    finally:
        # Stop server after the UI loop finishes, avoiding deadlock in wndproc
        try:
            server.stop()
        except Exception:
            pass


