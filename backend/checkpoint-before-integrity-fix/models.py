from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func

from app.db import Base


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    client_data = Column(Text)
    document_type = Column(String(100))
    generated_text = Column(Text)
    transaction_hash = Column(String(80), nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    sender = Column(String(80), nullable=True)
    document_hash = Column(String(80), nullable=True)


class DocumentStorage(Base):
    """Metadata for encrypted external document copies (never stores the encryption key)."""

    __tablename__ = "document_storage"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    provider = Column(String(32), nullable=False)
    cid = Column(String(255), nullable=False)
    content_sha256 = Column(String(64), nullable=False)
    encrypted = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)
