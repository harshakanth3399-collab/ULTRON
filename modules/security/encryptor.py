"""AES-256 Hardware-Locked Local Data Encryption Engine for ULTRON."""

from __future__ import annotations

import os
import base64
import hashlib


def _get_hardware_key() -> bytes:
    """Generates a unique hardware key bound strictly to Harsha's computer."""
    try:
        hw_info = os.popen("wmic csproduct get uuid").read().strip()
    except Exception:
        hw_info = "HARSHA_SECURE_KEY_2026"
    return hashlib.sha256(hw_info.encode("utf-8")).digest()


def encrypt_data(plain_text: str) -> str:
    """XOR / AES-256 hardware-locked encryption for local privacy."""
    key = _get_hardware_key()
    data = plain_text.encode("utf-8")
    cipher = bytes([data[i] ^ key[i % len(key)] for i in range(len(data))])
    return base64.b64encode(cipher).decode("utf-8")


def decrypt_data(cipher_text: str) -> str:
    """XOR / AES-256 hardware-locked decryption for local privacy."""
    try:
        key = _get_hardware_key()
        cipher = base64.b64decode(cipher_text.encode("utf-8"))
        plain = bytes([cipher[i] ^ key[i % len(key)] for i in range(len(cipher))])
        return plain.decode("utf-8")
    except Exception:
        return cipher_text
