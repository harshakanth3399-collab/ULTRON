"""ULTRON Assistant Main Entry Point."""
print("[BOOT] main.py started", flush=True)

import sys

from app import main as launch_app
print("[BOOT] app.py imported", flush=True)


def run():
    print("=" * 50, flush=True)
    print("          ULTRON 1.0 - HOLOGRAPHIC AI", flush=True)
    print("=" * 50, flush=True)
    print("[BOOT] entering main event loop", flush=True)
    return launch_app()


if __name__ == "__main__":
    raise SystemExit(run())