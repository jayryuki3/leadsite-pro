"""Simple encryption for API keys stored in settings."""
import base64
import os
import hashlib

_SECRET = os.environ.get("LEADSITE_SECRET_KEY", "leadsite-pro-local-dev-key-change-me")
_KEY = hashlib.sha256(_SECRET.encode()).digest()


def encrypt_value(plaintext: str) -> str:
    """Simple XOR + base64 encryption for local storage."""
    if not plaintext:
        return ""
    key_bytes = _KEY
    encrypted = bytes(
        b ^ key_bytes[i % len(key_bytes)]
        for i, b in enumerate(plaintext.encode("utf-8"))
    )
    return base64.b64encode(encrypted).decode("ascii")


def decrypt_value(ciphertext: str) -> str:
    """Decrypt a value encrypted with encrypt_value."""
    if not ciphertext:
        return ""
    try:
        encrypted = base64.b64decode(ciphertext)
        key_bytes = _KEY
        decrypted = bytes(
            b ^ key_bytes[i % len(key_bytes)]
            for i, b in enumerate(encrypted)
        )
        return decrypted.decode("utf-8")
    except Exception:
        return ciphertext
