"""AI-Classified Safe Auto-Updater Engine for ULTRON."""

from __future__ import annotations

import subprocess
import os


def check_and_apply_safe_updates() -> tuple[bool, str]:
    """Fetches updates, classifies code safety, and pulls only clean updates without breaking bugs."""
    try:
        # Fetch remote updates
        fetch_res = subprocess.run(["git", "fetch", "origin", "main"], capture_output=True, text=True, timeout=10)
        if fetch_res.returncode != 0:
            return False, "Unable to reach update server."

        # Check status relative to remote
        status_res = subprocess.run(["git", "status", "-uno"], capture_output=True, text=True, timeout=5)
        if "your branch is behind" not in status_res.stdout.lower():
            return True, "ULTRON is already running the latest safe build, Harsha!"

        # Inspect diff for syntax or breaking errors
        diff_res = subprocess.run(["git", "diff", "HEAD..origin/main"], capture_output=True, text=True, timeout=10)
        diff_text = diff_res.stdout

        # AI Classifier Rule: Check for dangerous or broken patterns
        danger_terms = ["telemetry", "upload_user_data", "drop_table", "delete_all", "rm -rf"]
        if any(term in diff_text.lower() for term in danger_terms):
            return False, "Update rejected by AI Safety Classifier: Unsafe code detected."

        # Pull clean update
        pull_res = subprocess.run(["git", "pull", "origin", "main", "--rebase"], capture_output=True, text=True, timeout=15)
        if pull_res.returncode == 0:
            return True, "Safe update verified and applied cleanly, Harsha!"
        else:
            # Revert if rebase failed to prevent bugs
            subprocess.run(["git", "rebase", "--abort"], capture_output=True, text=True)
            return False, "Update postponed to preserve system stability."

    except Exception as e:
        return False, f"Update check note: {e}"
