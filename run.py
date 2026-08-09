"""
ULTRON root entry point.
Run this file to start ULTRON: python run.py
"""
if __name__ == "__main__":
    # Windows multiprocessing safety guard — MUST be first
    import multiprocessing
    multiprocessing.freeze_support()

    import sys

    # ── Boot banner ──────────────────────────────────────────────────────────
    print("[BOOT] run.py started", flush=True)
    print("=" * 50, flush=True)
    print("          ULTRON 1.0 - HOLOGRAPHIC AI", flush=True)
    print("=" * 50, flush=True)

    # ── Launch app (import happens here, inside __main__ guard) ──────────────
    from app import main as launch_app
    print("[BOOT] app.py imported", flush=True)
    print("[BOOT] entering main event loop", flush=True)

    raise SystemExit(launch_app())
