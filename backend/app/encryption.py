"""Environment-keyed encryption helpers.

This module deliberately does not generate or persist encryption keys automatically.
Set ENCRYPTION_KEY to a valid Fernet key and store it in a secret manager or a private
local environment file. Losing the key makes encrypted data unrecoverable.
"""
from __future__ import annotations

import os
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken

_FERNET: Optional[Fernet] = None


def _get_fernet() -> Fernet:
    global _FERNET
    if _FERNET is None:
        key = os.getenv("ENCRYPTION_KEY", "").strip()
        if not key:
            raise RuntimeError("ENCRYPTION_KEY is required; automatic key-file generation is disabled.")
        try:
            _FERNET = Fernet(key.encode("ascii"))
        except (ValueError, UnicodeEncodeError) as exc:
            raise RuntimeError("ENCRYPTION_KEY is not a valid Fernet key.") from exc
    return _FERNET


def encrypt_bytes(data: bytes) -> bytes:
    return _get_fernet().encrypt(data)


def decrypt_bytes(token: bytes) -> bytes:
    return _get_fernet().decrypt(token)


def encrypt_file(input_path: str, output_path: str) -> None:
    if not os.path.isfile(input_path):
        raise FileNotFoundError(f"Input file not found: {input_path}")
    with open(input_path, "rb") as infile:
        encrypted = encrypt_bytes(infile.read())
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    with open(output_path, "wb") as outfile:
        outfile.write(encrypted)


def decrypt_file(input_path: str, output_path: str) -> None:
    if not os.path.isfile(input_path):
        raise FileNotFoundError(f"Input file not found: {input_path}")
    with open(input_path, "rb") as infile:
        plaintext = decrypt_bytes(infile.read())
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    with open(output_path, "wb") as outfile:
        outfile.write(plaintext)


def verify_bytes(token: bytes) -> bool:
    try:
        decrypt_bytes(token)
        return True
    except InvalidToken:
        return False
