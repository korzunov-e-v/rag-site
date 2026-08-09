from pathlib import Path

import magic
from docx import Document
from pypdf import PdfReader

DOCX_MIME_TYPE = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)


def extract_txt(file_path: Path) -> str:
    return file_path.read_text(encoding="utf-8-sig")


def extract_pdf(file_path: Path) -> str:
    reader = PdfReader(file_path)
    return "\n".join(
        text
        for page in reader.pages
        if (text := page.extract_text())
    )


def extract_docx(file_path: Path) -> str:
    document = Document(file_path)
    return "\n".join(
        paragraph.text
        for paragraph in document.paragraphs
        if paragraph.text
    )


def get_text(file_path: str | Path) -> str | None:
    path = Path(file_path)
    mime_type = magic.from_file(str(path), mime=True)

    if mime_type.startswith("text/"):
        return extract_txt(path)
    if mime_type == "application/pdf":
        return extract_pdf(path)
    if mime_type == DOCX_MIME_TYPE:
        return extract_docx(path)
    return None
