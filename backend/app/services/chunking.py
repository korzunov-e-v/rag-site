from dataclasses import dataclass

from llama_index.core.node_parser import SentenceSplitter

from backend.app.services.extraction import Section
from backend.app.settings import settings


@dataclass
class Chunk:
    text: str
    page: int | None = None


splitter = SentenceSplitter(
    chunk_size=settings.chunk_size,
    chunk_overlap=settings.chunk_overlap,
)


def split_text(text: str) -> list[str]:
    text = " ".join(text.split())

    if not text:
        return []

    return splitter.split_text(text)


def split_sections(sections: list[Section]) -> list[Chunk]:
    # Режем каждую страницу отдельно, чтобы у чанка был номер страницы.
    return [
        Chunk(text, page=section.page)
        for section in sections
        for text in split_text(section.text)
    ]
