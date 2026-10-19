import hashlib

import pytest
from cryptography.fernet import Fernet

from app.ipfs_storage import IPFSStorageError, PinataEncryptedStorage


class FakeResponse:
    def __init__(self, payload=None, content=b""):
        self._payload = payload or {}
        self.content = content

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload

    def iter_content(self, chunk_size=65536):
        for start in range(0, len(self.content), chunk_size):
            yield self.content[start:start + chunk_size]

    def close(self):
        return None


def test_ipfs_is_disabled_without_credentials(monkeypatch):
    monkeypatch.setenv("IPFS_PROVIDER", "pinata")
    monkeypatch.delenv("PINATA_JWT", raising=False)
    monkeypatch.delenv("IPFS_ENCRYPTION_KEY", raising=False)
    storage = PinataEncryptedStorage()
    assert not storage.is_configured
    with pytest.raises(IPFSStorageError, match="not configured"):
        storage.store_encrypted(b"private document", "document.pdf")


def test_ipfs_upload_encrypts_content_and_can_restore(monkeypatch):
    key = Fernet.generate_key()
    monkeypatch.setenv("IPFS_PROVIDER", "pinata")
    monkeypatch.setenv("PINATA_JWT", "test-token")
    monkeypatch.setenv("IPFS_ENCRYPTION_KEY", key.decode())
    storage = PinataEncryptedStorage()
    original = b"%PDF-1.7\nconfidential legal document\n"
    captured = {}

    def fake_post(url, **kwargs):
        captured["url"] = url
        captured["encrypted"] = kwargs["files"]["file"][1]
        return FakeResponse({"IpfsHash": "bafy-test-cid"})

    monkeypatch.setattr("app.ipfs_storage.requests.post", fake_post)
    result = storage.store_encrypted(original, "document.pdf")
    assert result["cid"] == "bafy-test-cid"
    assert result["encrypted"] == "true"
    assert result["content_sha256"] == hashlib.sha256(original).hexdigest()
    assert captured["encrypted"] != original
    assert Fernet(key).decrypt(captured["encrypted"]) == original

    monkeypatch.setattr(
        "app.ipfs_storage.requests.get",
        lambda url, **kwargs: FakeResponse(content=captured["encrypted"]),
    )
    restored = storage.retrieve_and_decrypt(result["cid"], result["content_sha256"])
    assert restored == original


def test_ipfs_rejects_wrong_key_or_tampered_content(monkeypatch):
    key = Fernet.generate_key()
    wrong_key = Fernet.generate_key()
    encrypted = Fernet(key).encrypt(b"document")
    monkeypatch.setenv("IPFS_PROVIDER", "pinata")
    monkeypatch.setenv("PINATA_JWT", "test-token")
    monkeypatch.setenv("IPFS_ENCRYPTION_KEY", wrong_key.decode())
    monkeypatch.setattr(
        "app.ipfs_storage.requests.get",
        lambda url, **kwargs: FakeResponse(content=encrypted),
    )
    with pytest.raises(IPFSStorageError, match="could not be decrypted"):
        PinataEncryptedStorage().retrieve_and_decrypt("bafy-test-cid")
