"""
ULTRON Assistant main.py
Kept for backward compatibility: python main.py still works.
All boot prints are guarded inside __main__ to prevent re-execution on import.
"""
import sys

if __name__ == "__main__":
    # Windows multiprocessing safety guard
    import multiprocessing
    multiprocessing.freeze_support()

    print("[BOOT] main.py started", flush=True)
    print("=" * 50, flush=True)
    print("          ULTRON 1.0 - HOLOGRAPHIC AI", flush=True)
    print("=" * 50, flush=True)

    from app import main as launch_app
    print("[BOOT] app.py imported", flush=True)
    print("[BOOT] entering main event loop", flush=True)

    raise SystemExit(launch_app())