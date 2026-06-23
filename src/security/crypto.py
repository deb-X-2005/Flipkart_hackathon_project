"""Symmetric encryption for sensitive fields at rest. ISO 27001 A.10.1.

Uses Fernet (AES-128-CBC + HMAC-SHA256). Key read from CRYPTO_KEY env (urlsafe b64).
Generate one with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
"""
import os
from functools import lru_cache
from cryptography.fernet import Fernet, InvalidToken


@lru_cache(maxsize=1)
def _cipher() -> Fernet:
    from src.security.secrets import get_secret
    key = get_secret("CRYPTO_KEY")
    if not key:
        raise RuntimeError("CRYPTO_KEY not set; cannot encrypt/decrypt sensitive fields")
    return Fernet(key.encode())


def encrypt(plaintext: str) -> str:
    if plaintext is None:
        return ""
    return _cipher().encrypt(plaintext.encode("utf-8")).decode("ascii")


def decrypt(token: str) -> str:
    if not token:
        return ""
    try:
        return _cipher().decrypt(token.encode("ascii")).decode("utf-8")
    except InvalidToken as e:
        raise ValueError("invalid ciphertext or wrong key") from e


def generate_key() -> str:
    return Fernet.generate_key().decode("ascii")
