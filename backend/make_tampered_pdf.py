from io import BytesIO
from reportlab.pdfgen import canvas
from PyPDF2 import PdfReader, PdfWriter

source = "pdfs/LegalDocument_1.pdf"
target = "pdfs/LegalDocument_1_tampered.pdf"

reader = PdfReader(source)
writer = PdfWriter()

for index, page in enumerate(reader.pages):
    if index == 0:
        width = float(page.mediabox.width)
        height = float(page.mediabox.height)

        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=(width, height))
        c.setFont("Helvetica-Bold", 22)
        c.drawString(72, height - 100, "TEST ALTERATION - NOT ORIGINAL")
        c.save()

        buffer.seek(0)
        overlay = PdfReader(buffer)
        page.merge_page(overlay.pages[0])

    writer.add_page(page)

metadata = {
    str(k): str(v)
    for k, v in (reader.metadata or {}).items()
    if isinstance(k, str) and isinstance(v, str)
}
writer.add_metadata(metadata)

with open(target, "wb") as output:
    writer.write(output)

print(f"Created altered test copy: {target}")
