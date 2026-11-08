"""Chunking strategies: fixed-size with overlap and sentence-based."""
from dataclasses import dataclass
from credobot.rag.kb import split_sentences

FIXED_SIZE: int = 200
FIXED_OVERLAP: int = 50
SENTENCES_PER_CHUNK: int = 2


@dataclass(frozen=True)
class Chunk:
    chunk_id: str  # f"{strategy}:{doc_id}:{idx:03d}"
    doc_id: str
    strategy: str  # "fixed" | "sentence"
    idx: int
    text: str


def fixed_chunks(
    doc_id: str,
    text: str,
    size: int = FIXED_SIZE,
    overlap: int = FIXED_OVERLAP,
) -> list[Chunk]:
    """Sliding window over characters with whitespace snapping."""
    assert 0 <= overlap < size, "overlap must satisfy 0 <= overlap < size"
    text = text.strip()
    if not text:
        return []

    step = size - overlap
    start = 0
    chunks: list[Chunk] = []
    idx = 0
    total_len = len(text)

    while start < total_len:
        end = min(start + size, total_len)
        if end < total_len:
            next_space = text.find(" ", end)
            if next_space != -1 and (next_space - end) <= 20:
                end = next_space

        chunk_text = text[start:end].strip()
        if chunks and len(chunk_text) < overlap:
            break

        chunks.append(
            Chunk(
                chunk_id=f"fixed:{doc_id}:{idx:03d}",
                doc_id=doc_id,
                strategy="fixed",
                idx=idx,
                text=chunk_text,
            )
        )
        idx += 1
        start += step
        if end >= total_len:
            break

    return chunks


def sentence_chunks(
    doc_id: str,
    text: str,
    n: int = SENTENCES_PER_CHUNK,
) -> list[Chunk]:
    """Group consecutive sentences into chunks of n (no overlap)."""
    assert n >= 1, "n must be >= 1"
    sentences = split_sentences(text)
    if not sentences:
        return []

    chunks: list[Chunk] = []
    idx = 0
    for i in range(0, len(sentences), n):
        group = sentences[i : i + n]
        chunk_text = " ".join(group).strip()
        chunks.append(
            Chunk(
                chunk_id=f"sentence:{doc_id}:{idx:03d}",
                doc_id=doc_id,
                strategy="sentence",
                idx=idx,
                text=chunk_text,
            )
        )
        idx += 1

    return chunks


def chunk_corpus(docs: list, strategy: str) -> list[Chunk]:
    """Chunk a list of KBDocs using the requested strategy."""
    chunks: list[Chunk] = []
    for d in docs:
        if strategy == "fixed":
            chunks.extend(fixed_chunks(d.doc_id, d.text))
        elif strategy == "sentence":
            chunks.extend(sentence_chunks(d.doc_id, d.text))
        else:
            raise ValueError(f"Unknown chunking strategy: {strategy}")
    return chunks

