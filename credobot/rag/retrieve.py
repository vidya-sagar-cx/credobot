"""RAG retrieval logic over ChromaDB collections."""
from dataclasses import dataclass
from typing import Any
from credobot import config, counters
from credobot.rag.embeddings import embed
from credobot.rag.index import COLLECTIONS, ensure_index, get_collection


@dataclass
class Hit:
    chunk_id: str
    doc_id: str
    text: str
    similarity: float  # 1.0 - cosine distance


def retrieve(
    query: str,
    collection: str | None = None,
    k: int = config.TOP_K,
    client: Any = None,
) -> list[Hit]:
    """Retrieve top-k chunks from ChromaDB collection ordered by cosine similarity."""
    target_coll = collection or config.DEPLOY_COLLECTION or COLLECTIONS["sentence"]
    ensure_index(client=client)
    counters.incr("chroma.query")

    q_emb = embed([query])
    coll = get_collection(target_coll, client=client)
    res = coll.query(
        query_embeddings=q_emb,
        n_results=k,
        include=["documents", "metadatas", "distances"],
    )

    hits: list[Hit] = []
    if res and res["documents"] and res["documents"][0]:
        ids = res["ids"][0]
        docs = res["documents"][0]
        metas = res["metadatas"][0]
        distances = res["distances"][0]

        for cid, doc, meta, dist in zip(ids, docs, metas, distances):
            sim = 1.0 - float(dist)
            hits.append(
                Hit(
                    chunk_id=cid,
                    doc_id=meta["doc_id"],
                    text=doc,
                    similarity=round(sim, 4),
                )
            )

    hits.sort(key=lambda h: h.similarity, reverse=True)
    return hits


def top1_similarity(hits: list[Hit]) -> float:
    """Return similarity of top-1 hit, or 0.0 if empty."""
    return hits[0].similarity if hits else 0.0
