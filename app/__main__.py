from __future__ import annotations

import argparse

from app.main import run_forever
from app.tray import run_tray_app


def main() -> None:
    p = argparse.ArgumentParser(prog="streamer-widgets")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8765)
    p.add_argument("--tray", action="store_true", help="Run with Windows tray UI (recommended).")
    args = p.parse_args()

    if args.tray:
        run_tray_app(host=args.host, port=args.port)
    else:
        run_forever(host=args.host, port=args.port)


if __name__ == "__main__":
    main()


