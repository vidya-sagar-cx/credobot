"""Unit and integration tests for query normalization and response caching."""
import concurrent.futures
import time
import pytest

from credobot import config, counters
from credobot.cache import (
    RESPONSE_CACHE,
    ResponseCache,
    cached_grounded_answer,
    normalize_query,
)
from credobot.rag.generate import GroundedAnswer


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("How is EMI  calculated?", "how is emi calculated"),
        ("  what is the PENALTY for prepaying a home loan? ", "what is the penalty for prepaying a home loan"),
        ("Documents for KYC!!!", "documents for kyc"),
        ("Personal Loan Eligibility...", "personal loan eligibility"),
        ("Minimum Balance;;;", "minimum balance"),
    ],
)
def test_normalize_query_equivalences(raw, expected):
    assert normalize_query(raw) == expected


def test_miss_then_hit():
    RESPONSE_CACHE.clear()
    counters.reset()

    q1 = "What documents are required to complete KYC?"
    q2 = "what documents are required to complete kyc?"

    ans1, hit1 = cached_grounded_answer(q1)
    assert hit1 is False
    assert ans1.grounded is True

    snap1 = counters.snapshot()
    chroma1 = snap1.get("chroma.query", 0)
    llm1 = snap1.get("llm.generate", 0)
    assert chroma1 > 0

    # Second call should be a cache hit
    ans2, hit2 = cached_grounded_answer(q2)
    assert hit2 is True
    assert ans2.answer == ans1.answer
    assert ans2.sources == ans1.sources

    snap2 = counters.snapshot()
    chroma2 = snap2.get("chroma.query", 0)
    llm2 = snap2.get("llm.generate", 0)

    # Counters must NOT increase on cache hit
    assert chroma2 == chroma1
    assert llm2 == llm1
    assert counters.get("cache.hit") == 1
    assert counters.get("cache.miss") == 1


def test_different_collection_different_key():
    cache = ResponseCache()
    k1 = cache.key("How is EMI calculated?", "kb_fixed")
    k2 = cache.key("How is EMI calculated?", "kb_sentence")
    assert k1 != k2
    assert "kb_fixed" in k1
    assert "kb_sentence" in k2


def test_lru_eviction():
    cache = ResponseCache(max_entries=2)
    dummy_ans1 = GroundedAnswer(query="q1", answer="a1", sources=[], context=[], grounded=True, fallback=False, top_similarity=0.9)
    dummy_ans2 = GroundedAnswer(query="q2", answer="a2", sources=[], context=[], grounded=True, fallback=False, top_similarity=0.9)
    dummy_ans3 = GroundedAnswer(query="q3", answer="a3", sources=[], context=[], grounded=True, fallback=False, top_similarity=0.9)

    cache.set("k1", dummy_ans1)
    cache.set("k2", dummy_ans2)
    assert cache.get("k1") == dummy_ans1  # Access k1 to make k2 LRU

    cache.set("k3", dummy_ans3)  # Evicts k2
    assert cache.get("k1") == dummy_ans1
    assert cache.get("k2") is None
    assert cache.get("k3") == dummy_ans3


def test_ttl_expiry(monkeypatch):
    cache = ResponseCache(max_entries=10, ttl_seconds=10.0)
    dummy = GroundedAnswer(query="q", answer="ans", sources=[], context=[], grounded=True, fallback=False, top_similarity=0.9)

    current_time = 100.0
    monkeypatch.setattr(time, "monotonic", lambda: current_time)

    cache.set("k1", dummy)
    assert cache.get("k1") == dummy

    # Advance time past TTL
    current_time = 115.0
    assert cache.get("k1") is None


def test_thread_safety_smoke():
    cache = ResponseCache(max_entries=50)
    dummy = GroundedAnswer(query="q", answer="val", sources=[], context=[], grounded=True, fallback=False, top_similarity=0.9)

    def worker(worker_id: int):
        for i in range(50):
            k = f"key_{worker_id}_{i % 10}"
            cache.set(k, dummy)
            _ = cache.get(k)

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(worker, i) for i in range(8)]
        for f in concurrent.futures.as_completed(futures):
            f.result()

    assert cache.stats()["size"] <= 50
