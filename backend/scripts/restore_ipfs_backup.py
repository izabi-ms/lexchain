"""Restore the latest encrypted IPFS PDF backup for a document ID.

Run from the backend directory after configuring PINATA_JWT, IPFS_ENCRYPTION_KEY,
and DATABASE_URL in .env:

    python scripts/restore_ipfs_backup.py --document-id 12 --output restored.pdf
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.db import SessionLocal  # noqa: E402
from app.ipfs_storage import PinataEncryptedStorage  # noqa: E402
from app.models import DocumentStorage  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Restore a LexChain encrypted IPFS backup.")
    parser.add_argument("--document-id", type=int, required=True, help="LexChain document ID")
    parser.add_argument("--output", type=Path, required=True, help="Path to write the restored PDF")
    args = parser.parse_args()

    session = SessionLocal()
    try:
        record = (
            session.query(DocumentStorage)
            .filter(DocumentStorage.document_id == args.document_id)
            .order_by(DocumentStorage.id.desc())
            .first()
        )
        if record is None:
            print("No IPFS backup record exists for this document ID.", file=sys.stderr)
            return 2
        storage = PinataEncryptedStorage()
        content = storage.retrieve_and_decrypt(record.cid, record.content_sha256)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(content)
        print(f"Restored encrypted IPFS backup to: {args.output.resolve()}")
        print("The decrypted content matched the stored SHA-256 integrity digest.")
        return 0
    except Exception as exc:
        print(f"Restore failed: {exc}", file=sys.stderr)
        return 1
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
