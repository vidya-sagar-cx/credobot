"""ChromaDB indexing and management for fixed and sentence collections."""
from pathlib import Path
from typing import Any
from credobot import config
from credobot.rag.chunking import (
    FIXED_OVERLAP,
    FIXED_SIZE,
    SENTENCES_PER_CHUNK,
    Chunk,
    chunk_corpus,
    fixed_chunks,
    sentence_chunks,
)
from credobot.rag.embeddings import embed
from credobot.rag.kb import load_kb

COLLECTIONS: dict[str, str] = {
    "fixed": "kb_fixed",
    "sentence": "kb_sentence",
}

_client_cache: dict[str, Any] = {}


def get_client(path: Path | None = None) -> Any:
    """Return a cached PersistentClient for the given directory."""
    import chromadb
    from chromadb.config import Settings

    target_path = Path(path or config.CHROMA_DIR).resolve()
    target_path.mkdir(parents=True, exist_ok=True)
    path_str = str(target_path)

    if path_str not in _client_cache:
        _client_cache[path_str] = chromadb.PersistentClient(
            path=path_str,
            settings=Settings(anonymized_telemetry=False),
        )
    return _client_cache[path_str]


def get_collection(name: str, client: Any = None) -> Any:
    """Get or create collection with cosine space and no internal embedding function."""
    if client is None:
        client = get_client()
    return client.get_or_create_collection(
        name=name,
        metadata={"hnsw:space": "cosine"},
        embedding_function=None,
    )


def upsert_chunks(collection: Any, chunks: list[Chunk]) -> int:
    """Upsert Chunk objects into a ChromaDB collection using external embeddings."""
    if not chunks:
        return 0
    ids = [c.chunk_id for c in chunks]
    documents = [c.text for c in chunks]
    embeddings = embed(documents)
    metadatas = [
        {"doc_id": c.doc_id, "strategy": c.strategy, "idx": c.idx} for c in chunks
    ]
    collection.upsert(
        ids=ids,
        documents=documents,
        embeddings=embeddings,
        metadatas=metadatas,
    )
    return len(chunks)


def build_index(kb_dir: Path | None = None, client: Any = None) -> dict[str, int]:
    """Chunk the KB both ways and upsert into both collections. Returns counts."""
    if client is None:
        client = get_client()
    docs = load_kb(kb_dir)
    counts: dict[str, int] = {}
    for strat, coll_name in COLLECTIONS.items():
        chunks = chunk_corpus(docs, strat)
        coll = get_collection(coll_name, client=client)
        upsert_chunks(coll, chunks)
        counts[coll_name] = coll.count()
    return counts


def add_document(doc_id: str, text: str, client: Any = None) -> dict[str, int]:
    """Chunk ONE new document both ways and upsert into both collections."""
    if client is None:
        client = get_client()
    counts: dict[str, int] = {}

    fc = fixed_chunks(doc_id, text)
    coll_fixed = get_collection(COLLECTIONS["fixed"], client=client)
    upsert_chunks(coll_fixed, fc)
    counts[COLLECTIONS["fixed"]] = coll_fixed.count()

    sc = sentence_chunks(doc_id, text)
    coll_sent = get_collection(COLLECTIONS["sentence"], client=client)
    upsert_chunks(coll_sent, sc)
    counts[COLLECTIONS["sentence"]] = coll_sent.count()

    return counts


def ensure_index(client: Any = None) -> None:
    """Build index if either collection is empty. Called lazily by retrieval."""
    if client is None:
        client = get_client()
    for coll_name in COLLECTIONS.values():
        coll = get_collection(coll_name, client=client)
        if coll.count() == 0:
            build_index(client=client)
            break


def main() -> int:
    """Build index, execute sample retrieval, and write transcript."""
    counts = build_index()
    print("=" * 60)
    print("CHROMA INDEX BUILD COMPLETE")
    print(f"kb_fixed count: {counts.get('kb_fixed', 0)}")
    print(f"kb_sentence count: {counts.get('kb_sentence', 0)}")
    print("=" * 60)

    sample_query = "How is EMI calculated?"
    q_emb = embed([sample_query])
    client = get_client()

    print(f"\nSample Query: '{sample_query}'")
    transcript_rows = []

    for coll_name in [COLLECTIONS["fixed"], COLLECTIONS["sentence"]]:
        coll = get_collection(coll_name, client=client)
        results = coll.query(
            query_embeddings=q_emb,
            n_results=3,
            include=["documents", "metadatas", "distances"],
        )
        print(f"\nResults for {coll_name}:")
        docs = results["documents"][0]
        metas = results["metadatas"][0]
        distances = results["distances"][0]
        ids = results["ids"][0]

        for rank, (cid, doc, meta, dist) in enumerate(
            zip(ids, docs, metas, distances), start=1
        ):
            print(
                f"  Rank {rank}: doc_id={meta['doc_id']} dist={dist:.4f} chunk_id={cid}"
            )
            print(f"          text: {doc[:80]}...")
            transcript_rows.append(
                [
                    coll_name,
                    str(rank),
                    cid,
                    meta["doc_id"],
                    f"{dist:.4f}",
                    doc[:75] + ("..." if len(doc) > 75 else ""),
                ]
            )

    try:
        from credobot.demos.transcript import Transcript

        t = Transcript("part1_index", "Part 1 — Chunking & Indexing")
        t.h2("Chunking Strategies Configuration")
        t.table(
            ["Strategy", "Collection Name", "Parameters"],
            [
                [
                    "Fixed-Size with Overlap",
                    COLLECTIONS["fixed"],
                    f"size={FIXED_SIZE} chars, overlap={FIXED_OVERLAP} chars",
                ],
                [
                    "Sentence-Based",
                    COLLECTIONS["sentence"],
                    f"sentences_per_chunk={SENTENCES_PER_CHUNK}",
                ],
            ],
        )

        t.h2("Indexed Chunk Counts")
        t.table(
            ["Collection", "Chunk Count"],
            [
                [COLLECTIONS["fixed"], str(counts.get(COLLECTIONS["fixed"], 0))],
                [COLLECTIONS["sentence"], str(counts.get(COLLECTIONS["sentence"], 0))],
            ],
        )

        t.h2(f"Sample Retrieval: '{sample_query}'")
        t.table(
            ["Collection", "Rank", "Chunk ID", "Doc ID", "Cosine Distance", "Snippet"],
            transcript_rows,
        )
        saved = t.save()
        print(f"\nTranscript written to: {saved}")
    except Exception as e:
        print(f"Failed to generate transcript: {e}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

