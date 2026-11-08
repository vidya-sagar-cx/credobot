"""Integration tests for ChromaDB indexing and retrieval."""
import pytest
from credobot.rag.embeddings import embed
from credobot.rag.index import (
    COLLECTIONS,
    add_document,
    build_index,
    get_client,
    get_collection,
)


def test_build_index_two_collections(isolated_env):
    client = get_client(isolated_env / "chroma")
    counts = build_index(client=client)

    assert COLLECTIONS["fixed"] in counts
    assert COLLECTIONS["sentence"] in counts
    assert counts[COLLECTIONS["fixed"]] > 0
    assert counts[COLLECTIONS["sentence"]] > 0
    # The two strategies produce different numbers of chunks
    assert counts[COLLECTIONS["fixed"]] != counts[COLLECTIONS["sentence"]]


def test_upsert_idempotent(isolated_env):
    client = get_client(isolated_env / "chroma")
    c1 = build_index(client=client)
    c2 = build_index(client=client)
    assert c1 == c2


def test_sample_query_sensible(isolated_env):
    client = get_client(isolated_env / "chroma")
    build_index(client=client)

    query = "How is EMI calculated?"
    q_emb = embed([query])

    for coll_name in COLLECTIONS.values():
        coll = get_collection(coll_name, client=client)
        res = coll.query(query_embeddings=q_emb, n_results=1, include=["metadatas"])
        top_meta = res["metadatas"][0][0]
        assert (
            top_meta["doc_id"] == "emi_calculation"
        ), f"Top result in {coll_name} was {top_meta['doc_id']}, expected emi_calculation"


def test_add_document(isolated_env):
    client = get_client(isolated_env / "chroma")
    initial_counts = build_index(client=client)

    doc_id = "test_custom_doc"
    doc_text = (
        "X Corp Bank special agricultural equipment subsidy loan details and terms. "
        "Eligible farmers receive subsidized interest rates on modern harvester purchases."
    )
    new_counts = add_document(doc_id, doc_text, client=client)

    assert new_counts[COLLECTIONS["fixed"]] > initial_counts[COLLECTIONS["fixed"]]
    assert new_counts[COLLECTIONS["sentence"]] > initial_counts[COLLECTIONS["sentence"]]

    # Verify retrievable
    q_emb = embed(["agricultural equipment subsidy harvester"])
    coll = get_collection(COLLECTIONS["sentence"], client=client)
    res = coll.query(query_embeddings=q_emb, n_results=1, include=["metadatas"])
    assert res["metadatas"][0][0]["doc_id"] == "test_custom_doc"

