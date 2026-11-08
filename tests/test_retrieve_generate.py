"""Unit and integration tests for retrieval and grounded generation."""
from credobot import config, counters
from credobot.rag.generate import IDK_MESSAGE, grounded_answer
from credobot.rag.index import COLLECTIONS, build_index, get_client
from credobot.rag.kb import split_sentences
from credobot.rag.queries import IN_SCOPE, OUT_OF_SCOPE
from credobot.rag.retrieve import retrieve, top1_similarity


def test_retrieve_sorted_and_bounded(isolated_env):
    client = get_client(isolated_env / "chroma")
    build_index(client=client)

    hits = retrieve("How is EMI calculated?", collection=COLLECTIONS["sentence"], k=3, client=client)
    assert len(hits) == 3
    for h in hits:
        assert -1.0 <= h.similarity <= 1.0
    for i in range(len(hits) - 1):
        assert hits[i].similarity >= hits[i + 1].similarity


def test_retrieve_counts_chroma_query(isolated_env):
    client = get_client(isolated_env / "chroma")
    build_index(client=client)

    counters.reset("chroma.query")
    assert counters.get("chroma.query") == 0
    retrieve("KYC documents", collection=COLLECTIONS["fixed"], client=client)
    assert counters.get("chroma.query") == 1


def test_threshold_separates_clusters(isolated_env):
    client = get_client(isolated_env / "chroma")
    build_index(client=client)

    threshold = config.IDK_THRESHOLD
    assert threshold is not None

    for coll_name in [COLLECTIONS["fixed"], COLLECTIONS["sentence"]]:
        for q, _ in IN_SCOPE:
            hits = retrieve(q, collection=coll_name, client=client)
            sim = top1_similarity(hits)
            assert sim >= threshold, f"In-scope query '{q}' in {coll_name} sim {sim} < {threshold}"

        for q in OUT_OF_SCOPE:
            hits = retrieve(q, collection=coll_name, client=client)
            sim = top1_similarity(hits)
            assert sim < threshold, f"Out-of-scope query '{q}' in {coll_name} sim {sim} >= {threshold}"


def test_in_scope_answer_grounded(isolated_env):
    client = get_client(isolated_env / "chroma")
    build_index(client=client)

    for q, _ in IN_SCOPE:
        ans = grounded_answer(q, collection=COLLECTIONS["sentence"], client=client)
        assert ans.fallback is False
        assert ans.grounded is True
        assert len(ans.sources) > 0

        # Verbatim check: every sentence in answer appears in at least one retrieved hit
        ans_sentences = split_sentences(ans.answer)
        hit_texts = [h.text for h in ans.context]
        for s in ans_sentences:
            found = any(s in ht for ht in hit_texts)
            assert found, f"Answer sentence '{s}' not found verbatim in any context hit"


def test_out_of_scope_fallback(isolated_env):
    client = get_client(isolated_env / "chroma")
    build_index(client=client)

    counters.reset("llm.generate")
    oos_q = OUT_OF_SCOPE[0]
    ans = grounded_answer(oos_q, collection=COLLECTIONS["sentence"], client=client)

    assert ans.fallback is True
    assert ans.grounded is False
    assert ans.answer == IDK_MESSAGE
    assert ans.sources == []
    assert counters.get("llm.generate") == 0
