from dataclasses import dataclass
from pathlib import Path

import magic
from docx import Document
from pypdf import PdfReader

DOCX_MIME_TYPE = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)


@dataclass
class Section:
    text: str
    page: int | None = None


def extract_txt(file_path: Path) -> list[Section]:
    return [Section(file_path.read_text(encoding="utf-8-sig"))]


def extract_pdf(file_path: Path) -> list[Section]:
    reader = PdfReader(file_path)
    return [
        Section(text, page=number)
        for number, page in enumerate(reader.pages, start=1)
        if (text := page.extract_text())
    ]


def extract_docx(file_path: Path) -> list[Section]:
    document = Document(file_path)
    return [
        Section(
            "\n".join(
                paragraph.text
                for paragraph in document.paragraphs
                if paragraph.text
            )
        )
    ]


def extract_sections(file_path: str | Path) -> list[Section] | None:
    path = Path(file_path)
    mime_type = magic.from_file(str(path), mime=True)

    if mime_type.startswith("text/"):
        return extract_txt(path)
    if mime_type == "application/pdf":
        return extract_pdf(path)
    if mime_type == DOCX_MIME_TYPE:
        return extract_docx(path)
    return None
