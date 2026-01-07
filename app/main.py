from __future__ import annotations

import asyncio
import os
import threading
from pathlib import Path
from typing import Optional

from aiohttp import web

from app.providers.gsmtc import run_gsmtc_provider
from app.state import AppState
from app.webserver import make_app


def _configure_asyncio() -> None:
    """
    Windows: avoid noisy Proactor transport errors on abrupt socket closes and
    improve compatibility by using the selector event loop policy.
    """
    if os.name == "nt":
        try:
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())  # type: ignore[attr-defined]
        except Exception:
            pass


def _install_loop_exception_handler(loop: asyncio.AbstractEventLoop) -> None:
    def handler(_loop: asyncio.AbstractEventLoop, context: dict) -> None:
        exc = context.get("exception")
        # Ignore common noisy Windows disconnect error (browser/tab closes etc.)
        if isinstance(exc, ConnectionResetError) and getattr(exc, "winerror", None) == 10054:
            return
        _loop.default_exception_handler(context)

    loop.set_exception_handler(handler)


async def _run_server(host: str, port: int, state: AppState) -> None:
    app = make_app(state)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()

    # Start providers
    asyncio.create_task(run_gsmtc_provider(state))

    while True:
        await asyncio.sleep(3600)


def run_forever(host: str = "127.0.0.1", port: int = 8765) -> None:
    """
    Blocking entrypoint for console usage.
    """
    _configure_asyncio()
    loop = asyncio.new_event_loop()
    _install_loop_exception_handler(loop)
    asyncio.set_event_loop(loop)
    state = AppState()
    try:
        loop.run_until_complete(_run_server(host, port, state))
    except KeyboardInterrupt:
        pass
    finally:
        loop.stop()
        loop.close()


class ServerController:
    """
    Starts/stops the asyncio server on a background thread (for tray UI).
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 8765) -> None:
        self.host = host
        self.port = port
        self._thread: Optional[threading.Thread] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._stop_evt = threading.Event()

    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        if self.is_running():
            return
        self._stop_evt.clear()

        def _thread_main() -> None:
            _configure_asyncio()
            loop = asyncio.new_event_loop()
            _install_loop_exception_handler(loop)
            self._loop = loop
            asyncio.set_event_loop(loop)

            state = AppState()

            async def runner() -> None:
                app = make_app(state)
                runner = web.AppRunner(app)
                await runner.setup()
                site = web.TCPSite(runner, self.host, self.port)
                await site.start()
                provider_task = asyncio.create_task(run_gsmtc_provider(state))

                try:
                    while not self._stop_evt.is_set():
                        await asyncio.sleep(0.2)
                finally:
                    provider_task.cancel()
                    # CancelledError may derive from BaseException depending on Python version;
                    # suppress it so Stop doesn't spam a traceback.
                    with contextlib.suppress(BaseException):
                        await provider_task
                    await runner.cleanup()

            import contextlib

            try:
                loop.run_until_complete(runner())
            except BaseException:
                # Avoid noisy background-thread tracebacks on intentional shutdown.
                pass
            finally:
                try:
                    loop.stop()
                finally:
                    loop.close()

        self._thread = threading.Thread(target=_thread_main, name="WidgetServer", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if not self.is_running():
            return
        self._stop_evt.set()
        if self._thread:
            # Wait for cleanup so the port is released before a subsequent start().
            self._thread.join()
        self._thread = None
        self._loop = None


