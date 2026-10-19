from typing import Any, Optional

from pydantic import BaseModel, Field


class GenerateStreamRequest(BaseModel):
    template_id: str | int
    fields: dict[str, Any] = Field(default_factory=dict)


class SaveDocumentRequest(BaseModel):
    client_data: str = Field(min_length=1, max_length=20000)
    document_type: str = Field(min_length=1, max_length=100)
    generated_text: str = Field(min_length=1, max_length=200000)
    date: Optional[str] = None


class DocumentRequest(BaseModel):
    client_data: str
    document_type: str


class DocumentResponse(BaseModel):
    document_id: int
    generated_text: str


class NotarizeRequest(BaseModel):
    document_id: int


class NotarizeResponse(BaseModel):
    transaction_hash: str
    document_hash: str
    pdf_hash: Optional[str] = None


class StatusResponse(BaseModel):
    transaction_hash: Optional[str] = None
    timestamp: Optional[str] = None
    document_hash: Optional[str] = None
    pdf_hash: Optional[str] = None

class SaveTxRequest(BaseModel):
    document_id: int
    transaction_hash: str = Field(min_length=10, max_length=80)
    document_hash: str = Field(min_length=10, max_length=80)
    sender: str = Field(min_length=10, max_length=80)


class HistoryDocumentResponse(BaseModel):
    document_id: int
    client_data: str
    document_type: str
    generated_text: str
    transaction_hash: Optional[str] = None
    document_hash: Optional[str] = None
    sender: Optional[str] = None
    timestamp: Optional[str] = None
    has_pdf: bool = False
