"""Text chunking for RAG."""
import re
from typing import Iterator

DEFAULT_CHUNK_SIZE = 800
DEFAULT_CHUNK_OVERLAP = 100


def _recursive_split(text: str, separators: list[str], chunk_size: int, overlap: int) -> list[str]:
    """Split text recursively by separators."""
    if not text or not text.strip():
        return []

    if len(text) <= chunk_size:
        return [text.strip()] if text.strip() else []

    sep = separators[0] if separators else ""
    if sep:
        parts = text.split(sep)
        if len(parts) > 1:
            chunks = []
            current = ""
            for part in parts:
                piece = part + sep if sep not in ("\n", " ") else part
                if len(current) + len(piece) <= chunk_size:
                    current += piece
                else:
                    if current.strip():
                        chunks.append(current.strip())
                    # Overlap
                    overlap_start = max(0, len(current) - overlap)
                    current = current[overlap_start:] + piece
            if current.strip():
                chunks.append(current.strip())
            return chunks

    # Fallback: split by character
    chunks = []
    for i in range(0, len(text), chunk_size - overlap):
        chunk = text[i : i + chunk_size]
        if chunk.strip():
            chunks.append(chunk.strip())
    return chunks


def chunk_text(
    text: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> list[str]:
    """Split text into overlapping chunks, respecting paragraph boundaries."""
    separators = ["\n\n", "\n", ". ", " ", ""]
    return _recursive_split(text, separators, chunk_size, overlap)


def chunk_documents(
    documents: Iterator[tuple[str, dict]],
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> Iterator[tuple[str, dict]]:
    """Chunk documents and yield (chunk_text, metadata) for each chunk."""
    for text, metadata in documents:
        chunks = chunk_text(text, chunk_size=chunk_size, overlap=overlap)
        for i, chunk in enumerate(chunks):
            chunk_meta = {**metadata, "chunk_index": i}
            yield chunk, chunk_meta
