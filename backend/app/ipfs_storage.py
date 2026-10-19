"""Optional encrypted document storage on Pinata/IPFS.

Plaintext documents are encrypted before leaving the backend. The encryption key is
provided out-of-band through IPFS_ENCRYPTION_KEY and is never uploaded to IPFS.
"""
from __future__ import annotations

import hashlib
import os
from typing import Any

import requests
from cryptography.fernet import Fernet, InvalidToken
from dotenv import load_dotenv

from app.db import BACKEND_DIR

load_dotenv(BACKEND_DIR / ".env", override=False)


class IPFSStorageError(RuntimeError):
    pass


class PinataEncryptedStorage:
    def __init__(self) -> None:
        self.provider = os.getenv("IPFS_PROVIDER", "pinata").strip().lower()
        self.jwt = os.getenv("PINATA_JWT", "").strip()
        self.gateway = os.getenv(
            "IPFS_GATEWAY_URL", "https://gateway.pinata.cloud/ipfs"
        ).rstrip("/")
        key = os.getenv("IPFS_ENCRYPTION_KEY", "").strip()
        self._fernet: Fernet | None = None
        if key:
            try:
                self._fernet = Fernet(key.encode("ascii"))
            except (ValueError, TypeError, UnicodeEncodeError):
                self._fernet = None

    @property
    def is_configured(self) -> bool:
        return self.provider == "pinata" and bool(self.jwt) and self._fernet is not None

    def store_encrypted(self, content: bytes, filename: str) -> dict[str, str]:
        if not self.is_configured:
            raise IPFSStorageError(
                "Encrypted IPFS storage is not configured. Set PINATA_JWT and a valid IPFS_ENCRYPTION_KEY."
            )
        if not content:
            raise IPFSStorageError("Cannot store an empty document.")
        if len(content) > 20 * 1024 * 1024:
            raise IPFSStorageError("Document exceeds the 20 MB IPFS upload limit.")

        assert self._fernet is not None
        content_sha256 = hashlib.sha256(content).hexdigest()
        encrypted_content = self._fernet.encrypt(content)
        safe_filename = os.path.basename(filename)[:180] or "document.pdf"
        try:
            response = requests.post(
                "https://api.pinata.cloud/pinning/pinFileToIPFS",
                headers={"Authorization": f"Bearer {self.jwt}"},
                files={"file": (f"{safe_filename}.encrypted", encrypted_content, "application/octet-stream")},
                data={
                    "pinataMetadata": '{"name":"LexChain encrypted document"}',
                    "pinataOptions": '{"cidVersion":1}',
                },
                timeout=45,
            )
            response.raise_for_status()
            result: dict[str, Any] = response.json()
            cid = result.get("IpfsHash")
            if not isinstance(cid, str) or not cid.strip():
                raise IPFSStorageError("IPFS provider did not return a valid content identifier.")
            return {"cid": cid, "content_sha256": content_sha256, "encrypted": "true"}
        except IPFSStorageError:
            raise
        except requests.RequestException as exc:
            raise IPFSStorageError(f"IPFS upload failed: {exc.__class__.__name__}.") from exc
        except ValueError as exc:
            raise IPFSStorageError("IPFS provider returned an invalid response.") from exc

    def unpin(self, cid: str) -> None:
        """Remove LexChain's Pinata pin. Other IPFS nodes may still retain the content."""
        if not self.jwt:
            raise IPFSStorageError("PINATA_JWT is required to remove the IPFS pin.")
        if not cid or "/" in cid or ".." in cid:
            raise IPFSStorageError("Invalid IPFS content identifier.")
        try:
            response = requests.delete(
                f"https://api.pinata.cloud/pinning/unpin/{cid}",
                headers={"Authorization": f"Bearer {self.jwt}"},
                timeout=30,
            )
            if response.status_code == 404:
                return  # Idempotent retry: the pin is already absent.
            response.raise_for_status()
        except requests.RequestException as exc:
            raise IPFSStorageError(f"IPFS unpin failed: {exc.__class__.__name__}.") from exc

    def retrieve_and_decrypt(self, cid: str, expected_sha256: str | None = None) -> bytes:
        if not self.is_configured:
            raise IPFSStorageError(
                "Encrypted IPFS storage is not configured. Set PINATA_JWT and IPFS_ENCRYPTION_KEY."
            )
        if not cid or "/" in cid or ".." in cid:
            raise IPFSStorageError("Invalid IPFS content identifier.")
        try:
            response = requests.get(f"{self.gateway}/{cid}", timeout=45, stream=True)
            response.raise_for_status()
            encrypted_chunks: list[bytes] = []
            total_bytes = 0
            for chunk in response.iter_content(chunk_size=64 * 1024):
                if not chunk:
                    continue
                total_bytes += len(chunk)
                if total_bytes > 21 * 1024 * 1024:
                    raise IPFSStorageError("Encrypted IPFS object exceeds the supported size limit.")
                encrypted_chunks.append(chunk)
            encrypted_content = b"".join(encrypted_chunks)
        except IPFSStorageError:
            raise
        except requests.RequestException as exc:
            raise IPFSStorageError(f"IPFS retrieval failed: {exc.__class__.__name__}.") from exc
        finally:
            if "response" in locals():
                response.close()

        assert self._fernet is not None
        try:
            plaintext = self._fernet.decrypt(encrypted_content)
        except InvalidToken as exc:
            raise IPFSStorageError("The stored file could not be decrypted; the key may be wrong or data altered.") from exc
        if expected_sha256 and hashlib.sha256(plaintext).hexdigest() != expected_sha256:
            raise IPFSStorageError("Retrieved document hash does not match the stored integrity digest.")
        return plaintext
