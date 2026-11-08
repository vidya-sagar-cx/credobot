"""Unit tests for chunking precision/recall evaluation and recommendation."""
from credobot.rag import eval_chunking
from credobot.rag.eval_chunking import PRRow, calc_f1, evaluate, macro, recommend, score_query
from credobot.rag.index import COLLECTIONS, build_index, get_client
from credobot.rag.queries import IN_SCOPE
from credobot.rag.retrieve import Hit


def test_pr_arithmetic_unit(monkeypatch):
    fake_hits = [
        Hit(chunk_id="c1", doc_id="doc_a", text="t1", similarity=0.9),
        Hit(chunk_id="c2", doc_id="doc_a", text="t2", similarity=0.8),
        Hit(chunk_id="c3", doc_id="doc_b", text="t3", similarity=0.7),
    ]
    monkeypatch.setattr(eval_chunking, "retrieve", lambda *args, **kwargs: fake_hits)

    row = score_query("dummy query", {"doc_a", "doc_c"}, "test_coll")
    assert row.retrieved_docs == ["doc_a", "doc_b"]
    assert row.hits == 1
    assert row.precision == 0.5
    assert row.recall == 0.5
    assert "1/2" in row.arithmetic()


def test_dedup_before_scoring(monkeypatch):
    fake_hits = [
        Hit(chunk_id="c1", doc_id="doc_x", text="t1", similarity=0.9),
        Hit(chunk_id="c2", doc_id="doc_x", text="t2", similarity=0.8),
        Hit(chunk_id="c3", doc_id="doc_x", text="t3", similarity=0.7),
    ]
    monkeypatch.setattr(eval_chunking, "retrieve", lambda *args, **kwargs: fake_hits)

    row = score_query("dummy query", {"doc_x"}, "test_coll")
    assert row.retrieved_docs == ["doc_x"]
    assert row.hits == 1
    assert row.precision == 1.0
    assert row.recall == 1.0


def test_evaluate_both_collections(isolated_env):
    client = get_client(isolated_env / "chroma")
    build_index(client=client)

    results = evaluate(client=client)
    assert COLLECTIONS["fixed"] in results
    assert COLLECTIONS["sentence"] in results
    assert len(results[COLLECTIONS["fixed"]]) == len(IN_SCOPE)
    assert len(results[COLLECTIONS["sentence"]]) == len(IN_SCOPE)

    for coll_name, rows in results.items():
        for r in rows:
            assert 0.0 <= r.precision <= 1.0
            assert 0.0 <= r.recall <= 1.0


def test_recommend_tiebreak():
    # Synthetic tiebreak: equal F1 and recall
    row_fixed = PRRow("q", "kb_fixed", [], ["d1"], {"d1"}, 1, 1.0, 1.0)
    row_sent = PRRow("q", "kb_sentence", [], ["d1"], {"d1"}, 1, 1.0, 1.0)

    synthetic_results = {
        "kb_fixed": [row_fixed],
        "kb_sentence": [row_sent],
    }
    winner, text = recommend(synthetic_results)
    assert winner == "kb_sentence"
    assert "kb_sentence" in text
