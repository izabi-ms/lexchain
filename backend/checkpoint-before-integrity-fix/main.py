from __future__ import annotations

import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional
from xml.sax.saxutils import escape

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from PyPDF2 import PdfReader, PdfWriter
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
from sqlalchemy.orm import Session

from app import blockchain, db, models, schemas
from app.ai_provider import AIProviderError, get_ai_provider
from app.ipfs_storage import IPFSStorageError, PinataEncryptedStorage

BACKEND_DIR = Path(__file__).resolve().parent
APP_DIR = BACKEND_DIR / "app"
TEMPLATES_PATH = APP_DIR / "templates.json"
PDF_DIR = BACKEND_DIR / "pdfs"
MAX_PDF_SIZE = 20 * 1024 * 1024

load_dotenv(BACKEND_DIR / ".env", override=False)
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger("lexchain")

app = FastAPI(
    title="LexChain API",
    description="AI-assisted document drafting and document-integrity services.",
    version="0.2.0",
)

allowed_origins = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS", "http://localhost:3000,http://localhost:5173"
    ).split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# Create tables for a local development baseline. A migration tool should replace this
# before a shared/production database is used.
models.Base.metadata.create_all(bind=db.engine)
PDF_DIR.mkdir(parents=True, exist_ok=True)


def _read_templates() -> list[dict]:
    try:
        import json
        with TEMPLATES_PATH.open("r", encoding="utf-8") as file:
            data = json.load(file)
        if not isinstance(data, list):
            raise ValueError("Template file must contain a list.")
        return data
    except (OSError, ValueError) as exc:
        logger.exception("Could not load the document template library")
        raise HTTPException(status_code=500, detail="The document template library could not be loaded.") from exc


def _pdf_path(document_id: int) -> Path:
    return PDF_DIR / f"LegalDocument_{document_id}.pdf"


def generate_pdf(document_text: str, document_id: int, file_path: Path) -> None:
    """Create a clean, neutral LexChain PDF without fabricated law-firm details."""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    styles = getSampleStyleSheet()
    brand_style = ParagraphStyle(
        "LexChainBrand", parent=styles["Title"], fontName="Helvetica-Bold",
        fontSize=17, leading=22, textColor=colors.HexColor("#172B4D"),
        spaceAfter=3,
    )
    subtitle_style = ParagraphStyle(
        "LexChainSubtitle", parent=styles["Normal"], fontSize=9,
        textColor=colors.HexColor("#5B6573"), spaceAfter=14,
    )
    heading_style = ParagraphStyle(
        "DocumentHeading", parent=styles["Heading2"], fontSize=12,
        leading=16, spaceBefore=12, spaceAfter=7,
        textColor=colors.HexColor("#172B4D"),
    )
    body_style = ParagraphStyle(
        "DocumentBody", parent=styles["BodyText"], fontSize=10.5,
        leading=15, spaceAfter=8, textColor=colors.HexColor("#202938"),
    )
    meta_style = ParagraphStyle(
        "DocumentMeta", parent=styles["Normal"], fontSize=8.5,
        leading=11, textColor=colors.HexColor("#5B6573"), spaceAfter=4,
    )

    document = SimpleDocTemplate(
        str(file_path), pagesize=letter,
        rightMargin=54, leftMargin=54, topMargin=48, bottomMargin=48,
        title=f"LexChain Document {document_id}", author="LexChain",
    )
    story = [
        Paragraph("LEXCHAIN", brand_style),
        Paragraph("AI-assisted document draft", subtitle_style),
        Paragraph(f"Document reference: {document_id}", meta_style),
        Paragraph(f"Generated: {datetime.now(timezone.utc).strftime('%d %B %Y, %H:%M UTC')}", meta_style),
        Spacer(1, 14),
    ]

    for raw_paragraph in re.split(r"\n\s*\n", document_text or ""):
        paragraph = raw_paragraph.strip()
        if not paragraph:
            continue
        plain_text = paragraph.replace("**", "")
        if (plain_text.isupper() and len(plain_text) < 100) or paragraph.startswith("**"):
            story.append(Paragraph(escape(plain_text), heading_style))
        else:
            # Escape user/model content so it cannot be interpreted as ReportLab markup.
            story.append(Paragraph(escape(plain_text).replace("\n", "<br/>"), body_style))

    story.extend([
        Spacer(1, 16),
        Paragraph(
            "<b>Important:</b> This document was generated with AI assistance and requires human review. "
            "It is not a substitute for advice from a qualified legal professional. A blockchain record, "
            "if present, records a digital hash and does not itself certify legal validity or the truth of the contents.",
            meta_style,
        ),
    ])
    document.build(story)


def _archive_encrypted_pdf(document_id: int, file_path: Path, session: Session) -> bool:
    """Optionally pin an encrypted PDF copy to IPFS; never upload plaintext to IPFS."""
    storage = PinataEncryptedStorage()
    if not storage.is_configured:
        return False
    try:
        content = file_path.read_bytes()
        result = storage.store_encrypted(content, file_path.name)
        session.add(models.DocumentStorage(
            document_id=document_id,
            provider="pinata",
            cid=result["cid"],
            content_sha256=result["content_sha256"],
            encrypted=True,
        ))
        session.commit()
        logger.info("Stored encrypted document %s on IPFS", document_id)
        return True
    except Exception as exc:
        session.rollback()
        # Cloud storage failure must not destroy a successfully saved local document.
        logger.warning("IPFS backup failed for document %s: %s", document_id, exc.__class__.__name__)
        return False


def _document_or_404(document_id: int, session: Session) -> models.Document:
    document = session.query(models.Document).filter(models.Document.id == document_id).first()
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found.")
    return document


@app.get("/health")
def health_check():
    provider_name = os.getenv("AI_PROVIDER", "nvidia_nim").strip().lower()
    try:
        provider = get_ai_provider()
        provider_configured = provider.is_configured
    except AIProviderError:
        provider_configured = False
    return {
        "status": "ok",
        "service": "lexchain-api",
        "ai_provider": provider_name,
        "ai_provider_configured": provider_configured,
        "ipfs_configured": PinataEncryptedStorage().is_configured,
        "blockchain_configured": all(os.getenv(name, "").strip() for name in (
            "INFURA_URL", "CONTRACT_ADDRESS", "ACCOUNT_ADDRESS", "PRIVATE_KEY"
        )),
    }


@app.post("/generate/stream")
async def stream_generate(request: schemas.GenerateStreamRequest):
    templates = _read_templates()
    template = next((item for item in templates if str(item.get("id")) == str(request.template_id)), None)
    if template is None:
        raise HTTPException(status_code=400, detail="Invalid document template.")

    fields = request.fields
    if not isinstance(fields, dict):
        raise HTTPException(status_code=422, detail="Please complete the document form fields.")
    template_fields = template.get("fields", [])
    missing = [
        field.get("label", field.get("id", "Required field"))
        for field in template_fields
        if field.get("id") and field.get("required", True)
        and not str(fields.get(field["id"], "")).strip()
    ]
    if missing:
        raise HTTPException(status_code=422, detail={"message": "Complete all required fields.", "missing_fields": missing})

    try:
        prompt = template["ai_prompt"].format(**fields)
    except (KeyError, ValueError) as exc:
        logger.warning("Invalid prompt placeholders in template %s", template.get("id"))
        raise HTTPException(status_code=500, detail="This template needs configuration before it can be used.") from exc

    try:
        provider = get_ai_provider()
        client, provider_response = await provider.open_stream(prompt)
    except AIProviderError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    async def stream_response():
        try:
            async for chunk in provider.stream_text(provider_response):
                yield chunk
        except Exception:
            logger.exception("NVIDIA NIM stream failed after response started")
        finally:
            await provider_response.aclose()
            await client.aclose()

    return StreamingResponse(
        stream_response(),
        media_type="text/plain; charset=utf-8",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/notarize", response_model=schemas.NotarizeResponse)
def notarize_document(request: schemas.NotarizeRequest, session: Session = Depends(db.get_db)):
    document = _document_or_404(request.document_id, session)
    try:
        service = blockchain.get_blockchain_service()
        document_hash = service.hash_document(document.generated_text)
        transaction_hash = service.notarize_hash_on_chain(document_hash)
    except (blockchain.BlockchainConfigurationError, RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    document.transaction_hash = transaction_hash
    document.document_hash = document_hash
    document.timestamp = datetime.now(timezone.utc)
    session.commit()
    pdf_path = _pdf_path(document.id)
    generate_pdf(document.generated_text, document.id, pdf_path)
    _archive_encrypted_pdf(document.id, pdf_path, session)
    return schemas.NotarizeResponse(transaction_hash=transaction_hash, document_hash=document_hash)


@app.get("/status/{document_id}", response_model=schemas.StatusResponse)
def document_status(document_id: int, session: Session = Depends(db.get_db)):
    document = _document_or_404(document_id, session)
    document_hash = document.document_hash
    if not document_hash:
        try:
            document_hash = blockchain.get_blockchain_service().hash_document(document.generated_text)
        except (blockchain.BlockchainConfigurationError, RuntimeError, ValueError):
            document_hash = None
    return schemas.StatusResponse(
        transaction_hash=document.transaction_hash,
        timestamp=document.timestamp.isoformat() if document.timestamp else None,
        document_hash=document_hash,
    )


@app.post("/saveTx")
def save_transaction(data: schemas.SaveTxRequest, session: Session = Depends(db.get_db)):
    document = _document_or_404(data.document_id, session)
    try:
        service = blockchain.get_blockchain_service()
        expected_hash = service.hash_document(document.generated_text)
        if expected_hash.lower() != data.document_hash.lower():
            raise HTTPException(status_code=422, detail="Submitted document hash does not match the saved document.")
        verification = service.verify_transaction(
            data.transaction_hash,
            expected_hash,
            expected_sender=data.sender,
        )
    except HTTPException:
        raise
    except (blockchain.BlockchainConfigurationError, RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    document.transaction_hash = verification["transaction_hash"]
    document.sender = verification["sender"]
    document.document_hash = expected_hash
    document.timestamp = datetime.fromtimestamp(int(verification["timestamp"]), tz=timezone.utc)
    session.commit()

    pdf_path = _pdf_path(document.id)
    generate_pdf(document.generated_text, document.id, pdf_path)
    _archive_encrypted_pdf(document.id, pdf_path, session)
    return {"status": "success", "verified": True}


@app.get("/history", response_model=List[schemas.HistoryDocumentResponse])
def get_history(sender: Optional[str] = None, session: Session = Depends(db.get_db)):
    query = session.query(models.Document)
    if sender:
        query = query.filter(models.Document.sender.ilike(sender))
    documents = query.order_by(models.Document.timestamp.desc()).all()
    return [
        schemas.HistoryDocumentResponse(
            document_id=document.id,
            client_data=document.client_data or "",
            document_type=document.document_type or "Untitled",
            generated_text=document.generated_text or "",
            transaction_hash=document.transaction_hash,
            document_hash=document.document_hash,
            sender=document.sender,
            timestamp=document.timestamp.isoformat() if document.timestamp else None,
            has_pdf=_pdf_path(document.id).is_file(),
        )
        for document in documents
    ]


@app.post("/savePdf")
async def save_pdf(document_id: int, pdf: UploadFile = File(...), session: Session = Depends(db.get_db)):
    _document_or_404(document_id, session)
    if pdf.content_type not in ("application/pdf", "application/octet-stream"):
        raise HTTPException(status_code=415, detail="Only PDF documents are accepted.")
    content = await pdf.read(MAX_PDF_SIZE + 1)
    if len(content) > MAX_PDF_SIZE:
        raise HTTPException(status_code=413, detail="PDF exceeds the 20 MB upload limit.")
    if not content.startswith(b"%PDF-"):
        raise HTTPException(status_code=415, detail="The uploaded file does not appear to be a valid PDF.")

    target_path = _pdf_path(document_id)
    temporary_path = target_path.with_suffix(".uploading")
    try:
        temporary_path.write_bytes(content)
        temporary_path.replace(target_path)
    except OSError as exc:
        temporary_path.unlink(missing_ok=True)
        logger.exception("Could not save uploaded PDF")
        raise HTTPException(status_code=500, detail="Could not save the PDF.") from exc

    ipfs_backup = _archive_encrypted_pdf(document_id, target_path, session)
    return {"status": "pdf saved", "ipfs_backup": "stored_encrypted" if ipfs_backup else "not_configured_or_failed"}


@app.get("/pdf/{document_id}")
def get_pdf(document_id: int, session: Session = Depends(db.get_db)):
    _document_or_404(document_id, session)
    file_path = _pdf_path(document_id)
    if file_path.is_file():
        return FileResponse(file_path, media_type="application/pdf", filename=f"LexChain_Document_{document_id}.pdf")
    raise HTTPException(status_code=404, detail="PDF not found.")


@app.get("/templates")
def get_templates():
    return _read_templates()


@app.post("/document")
def save_generated_document(data: schemas.SaveDocumentRequest, session: Session = Depends(db.get_db)):
    document = models.Document(
        client_data=data.client_data,
        document_type=data.document_type,
        generated_text=data.generated_text,
    )
    session.add(document)
    session.commit()
    session.refresh(document)
    return {"document_id": document.id}


@app.delete("/document/{document_id}")
def delete_document(document_id: int, session: Session = Depends(db.get_db)):
    document = _document_or_404(document_id, session)
    storage_records = session.query(models.DocumentStorage).filter(
        models.DocumentStorage.document_id == document_id
    ).all()
    ipfs_storage = PinataEncryptedStorage()
    if storage_records and not ipfs_storage.jwt:
        raise HTTPException(
            status_code=409,
            detail="This document has an IPFS backup. Configure PINATA_JWT before deleting it so LexChain can request unpinning.",
        )
    for storage_record in storage_records:
        try:
            ipfs_storage.unpin(storage_record.cid)
        except IPFSStorageError as exc:
            raise HTTPException(
                status_code=502,
                detail="LexChain could not remove the document's IPFS pin. The document was not deleted; try again later.",
            ) from exc

    file_path = _pdf_path(document_id)
    if file_path.is_file():
        file_path.unlink()
    session.query(models.DocumentStorage).filter(
        models.DocumentStorage.document_id == document_id
    ).delete(synchronize_session=False)
    session.delete(document)
    session.commit()
    return {"status": "deleted", "ipfs_pins_requested_for_removal": len(storage_records)}


def watermark_text(document_id: int, document_hash: str) -> str:
    return f"LexChainID:{document_id};Hash:{document_hash}"


def add_pdf_metadata_watermark(input_path: Path, output_path: Path, watermark: str) -> None:
    from io import BytesIO
    reader = PdfReader(BytesIO(input_path.read_bytes()))
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    metadata = dict(reader.metadata) if reader.metadata else {}
    metadata["/LexChainDocumentReference"] = watermark
    writer.add_metadata(metadata)
    temporary_path = output_path.with_suffix(".watermarking")
    with temporary_path.open("wb") as output_file:
        writer.write(output_file)
    temporary_path.replace(output_path)


def has_watermark(pdf_path: Path, document_id: int, document_hash: str) -> bool:
    try:
        reader = PdfReader(str(pdf_path))
        marker = reader.metadata.get("/LexChainDocumentReference") if reader.metadata else None
        return marker == watermark_text(document_id, document_hash)
    except Exception:
        return False


@app.post("/watermark_pdf/{document_id}")
def watermark_pdf(document_id: int, session: Session = Depends(db.get_db)):
    document = _document_or_404(document_id, session)
    if not document.document_hash:
        raise HTTPException(status_code=409, detail="Notarize the saved document before adding its reference marker.")
    pdf_path = _pdf_path(document_id)
    if not pdf_path.is_file():
        generate_pdf(document.generated_text, document.id, pdf_path)
    try:
        add_pdf_metadata_watermark(
            input_path=pdf_path,
            output_path=pdf_path,
            watermark=watermark_text(document_id, document.document_hash),
        )
    except Exception as exc:
        logger.exception("Could not add the LexChain PDF reference marker")
        raise HTTPException(status_code=500, detail="Could not add the document reference marker.") from exc
    _archive_encrypted_pdf(document.id, pdf_path, session)
    return {"status": "reference_marker_added"}


@app.post("/verify_pdf/{document_id}")
async def verify_pdf(document_id: int, file: UploadFile = File(...), session: Session = Depends(db.get_db)):
    document = _document_or_404(document_id, session)
    if not document.document_hash:
        return {
            "valid": False,
            "reason": "No recorded document hash is available.",
            "verification_level": "metadata_marker_only",
        }
    content = await file.read(MAX_PDF_SIZE + 1)
    if len(content) > MAX_PDF_SIZE:
        raise HTTPException(status_code=413, detail="PDF exceeds the 20 MB upload limit.")
    if not content.startswith(b"%PDF-"):
        raise HTTPException(status_code=415, detail="The uploaded file does not appear to be a valid PDF.")
    try:
        from io import BytesIO
        reader = PdfReader(BytesIO(content))
        marker = reader.metadata.get("/LexChainDocumentReference") if reader.metadata else None
        valid = marker == watermark_text(document_id, document.document_hash)
        return {
            "valid": valid,
            "reason": (
                "The LexChain reference marker matches. This checks PDF metadata only; it is not yet a full content-integrity proof."
                if valid else "The expected LexChain reference marker is missing or does not match."
            ),
            "verification_level": "metadata_marker_only",
        }
    except Exception:
        return {
            "valid": False,
            "reason": "The uploaded PDF could not be read.",
            "verification_level": "metadata_marker_only",
        }
