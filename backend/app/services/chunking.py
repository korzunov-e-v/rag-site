from llama_index.core.node_parser import SentenceSplitter


splitter = SentenceSplitter(
    chunk_size=500,
    chunk_overlap=50,
)


def split_text(text: str) -> list[str]:
    text = " ".join(text.split())
    return splitter.split_text(text)
