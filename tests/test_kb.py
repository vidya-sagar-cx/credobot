"""Unit tests for knowledge base documents and loader."""
from credobot.rag.kb import REQUIRED_TOPICS, load_kb, split_sentences


def test_at_least_12_docs():
    docs = load_kb()
    assert len(docs) >= 12


def test_every_required_topic_has_doc():
    docs = load_kb()
    doc_ids = {d.doc_id for d in docs}
    for topic, doc_id in REQUIRED_TOPICS.items():
        assert doc_id in doc_ids, f"Required topic '{topic}' ({doc_id}) missing from KB"


def test_sentence_counts():
    docs = load_kb()
    for d in docs:
        sentences = split_sentences(d.text)
        assert 2 <= len(sentences) <= 5, f"Doc {d.doc_id} sentence count {len(sentences)} not in [2, 5]"


def test_utf8_and_nonempty():
    docs = load_kb()
    for d in docs:
        assert d.text.strip() != "", f"Doc {d.doc_id} is empty"
        assert d.path.exists()
        raw = d.path.read_bytes()
        decoded = raw.decode("utf-8")
        assert decoded.strip() == d.text


def test_split_sentences_basic():
    text1 = "A b. C d! E f?"
    s1 = split_sentences(text1)
    assert len(s1) == 3
    assert s1 == ["A b.", "C d!", "E f?"]

    text2 = "₹10,000 fee. Next."
    s2 = split_sentences(text2)
    assert len(s2) == 2
    assert s2 == ["₹10,000 fee.", "Next."]
