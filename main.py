"""ULTRON Assistant Main Entry Point."""

import sys
from app import main as launch_app


def run():
    print("=" * 50)
    print("          ULTRON 1.0 - HOLOGRAPHIC AI")
    print("=" * 50)
    return launch_app()


if __name__ == "__main__":
    raise SystemExit(run())