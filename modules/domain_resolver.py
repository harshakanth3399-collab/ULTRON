"""
modules/domain_resolver.py - ULTRON Domain & HTTPS Tunnel Bridge

Enables:
1. Local Domain Resolution for ultron.ai:
   - Maps 127.0.0.1 -> ultron.ai in Windows hosts file so typing http://ultron.ai:8000
     opens the ULTRON Assistant directly on the laptop.
2. Free Secure Worldwide HTTPS Tunnel:
   - Uses zero-config localtunnel/cloudflared to provide a public https:// link
     so phone can connect from anywhere on mobile 5G or remote Wi-Fi with full HTTPS.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import threading
import time
from typing import Optional, Tuple

HOSTS_PATH = r"C:\Windows\System32\drivers\etc\hosts"


class DomainResolver:
    """Manages domain mapping for ultron.ai and worldwide HTTPS tunnels."""

    def __init__(self) -> None:
        self._tunnel_process: Optional[subprocess.Popen] = None
        self._public_https_url: Optional[str] = None
        self._lock = threading.Lock()

    def is_local_domain_mapped(self) -> bool:
        """Checks if 127.0.0.1 is mapped to ultron.ai in Windows hosts file."""
        if not os.path.exists(HOSTS_PATH):
            return False
        try:
            with open(HOSTS_PATH, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            return bool(re.search(r"^\s*127\.0\.0\.1\s+ultron\.ai\b", content, re.MULTILINE))
        except Exception:
            return False

    def setup_local_domain(self) -> Tuple[bool, str]:
        """Adds '127.0.0.1 ultron.ai' to Windows hosts file if run as administrator."""
        if self.is_local_domain_mapped():
            return True, "ultron.ai is already mapped to 127.0.0.1 on your laptop!"

        entry = "\n127.0.0.1 ultron.ai\n"
        try:
            with open(HOSTS_PATH, "a", encoding="utf-8") as f:
                f.write(entry)
            return True, "Successfully mapped ultron.ai -> 127.0.0.1! You can now open http://ultron.ai:8000."
        except PermissionError:
            # Provide PowerShell command to run as admin
            return False, (
                "Permission required to modify Windows hosts file. To map ultron.ai permanently, "
                "run PowerShell as Administrator and execute:\n"
                'Add-Content -Path "C:\\Windows\\System32\\drivers\\etc\\hosts" -Value "`n127.0.0.1 ultron.ai"'
            )
        except Exception as e:
            return False, f"Failed to map domain: {e}"

    def start_free_https_tunnel(self, port: int = 8000, subdomain: str = "ultron-ai") -> Tuple[bool, str]:
        """Starts a free, zero-config HTTPS tunnel for worldwide phone access."""
        with self._lock:
            if self._tunnel_process and self._tunnel_process.poll() is None:
                return True, f"Worldwide HTTPS tunnel is already active: {self._public_https_url or 'Connecting...'}"

            # Check for npx
            npx_path = shutil.which("npx") or shutil.which("npx.cmd")
            if not npx_path:
                return False, "Node.js npx not found. Ensure Node is in PATH to generate public HTTPS links."

            def _run():
                try:
                    cmd = [npx_path, "localtunnel", "--port", str(port), "--subdomain", subdomain]
                    self._tunnel_process = subprocess.Popen(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        bufsize=1,
                    )
                    for line in iter(self._tunnel_process.stdout.readline, ""):
                        line_str = line.strip()
                        if "your url is:" in line_str.lower():
                            url = line_str.split(":", 1)[1].strip()
                            self._public_https_url = url
                            print(f"\n[ULTRON TUNNEL] Worldwide HTTPS Link Active -> {url}\n")
                            # Announce via speech
                            try:
                                from speech_engine import speak
                                speak("Worldwide HTTPS tunnel active for ULTRON.")
                            except Exception:
                                pass
                except Exception as e:
                    print(f"[TUNNEL ERROR] {e}")

            t = threading.Thread(target=_run, daemon=True)
            t.start()
            return True, "Starting free worldwide HTTPS tunnel in background. Link will be available in seconds."

    def get_public_url(self) -> Optional[str]:
        return self._public_https_url


# Global Singleton
domain_resolver = DomainResolver()
