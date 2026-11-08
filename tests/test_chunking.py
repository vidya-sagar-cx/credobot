"""Unit tests for fixed and sentence chunking."""
import pytest
from credobot.rag.chunking import (
    FIXED_OVERLAP,
    FIXED_SIZE,
    SENTENCES_PER_CHUNK,
    Chunk,
    fixed_chunks,
    sentence_chunks,
)


def test_fixed_overlap():
    text = (
        "Alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu nu xi omicron pi "
        "rho sigma tau upsilon phi chi psi omega. " * 5
    )
    assert len(text) >= 600
    chunks = fixed_chunks("test_doc", text, size=200, overlap=50)
    assert len(chunks) > 1

    for i in range(len(chunks) - 1):
        c1 = chunks[i].text
        c2 = chunks[i + 1].text
        # Find shared suffix of c1 and prefix of c2
        shared_found = False
        for k in range(30, min(len(c1), len(c2)) + 1):
            if c1.endswith(c2[:k]):
                shared_found = True
                break
        assert shared_found, f"Chunks {i} and {i+1} do not exhibit sufficient overlap"


def test_fixed_covers_text():
    sample = (
        "The quick brown fox jumps over the lazy dog. A swift lending review allows instant "
        "verification and seamless processing of credit records across branches."
    )
    chunks = fixed_chunks("sample_doc", sample, size=50, overlap=15)
    for word in sample.split():
        found = any(word in c.text for c in chunks)
        assert found, f"Word '{word}' missing from fixed chunks"


def test_sentence_grouping():
    text = "Sentence one. Sentence two! Sentence three? Sentence four. Sentence five."
    chunks = sentence_chunks("sent_doc", text, n=2)
    assert len(chunks) == 3
    assert chunks[0].text == "Sentence one. Sentence two!"
    assert chunks[1].text == "Sentence three? Sentence four."
    assert chunks[2].text == "Sentence five."


def test_chunk_ids_stable():
    text = "Short text for stability checking. Sentence two."
    c1 = fixed_chunks("doc_a", text)
    c2 = fixed_chunks("doc_a", text)
    assert [c.chunk_id for c in c1] == [c.chunk_id for c in c2]

    s1 = sentence_chunks("doc_a", text)
    s2 = sentence_chunks("doc_a", text)
    assert [s.chunk_id for s in s1] == [s.chunk_id for s in s2]


def test_invalid_overlap_raises():
    with pytest.raises(AssertionError):
        fixed_chunks("bad", "Some text", size=100, overlap=100)
    with pytest.raises(AssertionError):
        fixed_chunks("bad", "Some text", size=100, overlap=-5)
    with pytest.raises(AssertionError):
        sentence_chunks("bad", "Some text", n=0)

