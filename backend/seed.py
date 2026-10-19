from app.db import SessionLocal
from app.models import Document

def seed():
    db = SessionLocal()
    doc = Document(
        client_data="John Doe, Passport 123456",
        document_type="Affidavit",
        generated_text="This is a sample affidavit for John Doe."
    )
    db.add(doc)
    db.commit()
    db.close()

if __name__ == "__main__":
    seed()