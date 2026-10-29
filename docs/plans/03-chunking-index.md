# Plan 03 — Chunking strategies & ChromaDB indexing

## Goal
Two chunking strategies over the KB, embedded with a local SentenceTransformers model and
upserted into two separate persistent ChromaDB collections, rebuildable via one command.

## Brief tasks
T3. Acceptance: "Both chunking strategies are implemented, embedded, and indexed into two
separate ChromaDB collections that both produce sensible retrieval on a sample query."

## Depends on
02

## Read first
`credobot/rag/kb.py` (`load_kb`, `split_sentences`), `credobot/config.py`.

## Files
```
+ credobot/rag/chunking.py
+ credobot/rag/embeddings.py
+ credobot/rag/index.py
+ tests/test_chunking.py
+ tests/test_index.py
+ transcripts/part1_index.md   (generated)
```

## Code changes

### `credobot/rag/chunking.py`
```python
@dataclass(frozen=True)
class Chunk:
    chunk_id: str      # f"{strategy}:{doc_id}:{idx:03d}"  (stable → upsert is idempotent)
    doc_id: str
    strategy: str      # "fixed" | "sentence"
    idx: int
    text: str

FIXED_SIZE = 200       # characters
FIXED_OVERLAP = 50
SENTENCES_PER_CHUNK = 2

def fixed_chunks(doc_id, text, size=FIXED_SIZE, overlap=FIXED_OVERLAP) -> list[Chunk]:
    """Sliding window over characters, step = size - overlap; snap the window end
    forward to the next whitespace (max +20 chars) so words aren't cut; drop a final
    window shorter than `overlap` (it is fully contained in the previous one).
    Assert 0 <= overlap < size."""

def sentence_chunks(doc_id, text, n=SENTENCES_PER_CHUNK) -> list[Chunk]:
    """Group consecutive sentences from split_sentences() into chunks of n (no overlap)."""

def chunk_corpus(docs, strategy) -> list[Chunk]
```

### `credobot/rag/embeddings.py`
```python
from credobot import config
@lru_cache(maxsize=1)
def get_model() -> SentenceTransformer:
    return SentenceTransformer(config.EMBED_MODEL, device="cpu")

def embed(texts: list[str]) -> list[list[float]]:
    return get_model().encode(texts, normalize_embeddings=True,
                              convert_to_numpy=True).tolist()
```
Import `sentence_transformers` lazily inside `get_model` so modules importing
`embeddings` stay cheap.

### `credobot/rag/index.py`
```python
COLLECTIONS = {"fixed": "kb_fixed", "sentence": "kb_sentence"}

def get_client(path: Path | None = None) -> chromadb.ClientAPI:
    """PersistentClient(path=str(path or config.CHROMA_DIR),
       settings=Settings(anonymized_telemetry=False)). Cache per path."""

def get_collection(name: str, client=None) -> Collection:
    return client.get_or_create_collection(name, metadata={"hnsw:space": "cosine"},
                                           embedding_function=None)

def upsert_chunks(collection, chunks: list[Chunk]) -> int:
    collection.upsert(ids=[c.chunk_id ...], documents=[c.text ...],
                      embeddings=embed([c.text ...]),
                      metadatas=[{"doc_id": c.doc_id, "strategy": c.strategy, "idx": c.idx}])

def build_index(kb_dir=None, client=None) -> dict[str, int]:
    """Chunk the KB both ways, upsert into both collections. Returns counts."""

def add_document(doc_id: str, text: str, client=None) -> dict[str, int]:
    """Chunk ONE new document both ways and upsert into both collections.
    Reused by POST /add-document (plan 15). Does not write to kb/."""

def ensure_index(client=None) -> None:
    """build_index() if either collection is empty. Called lazily by retrieval."""

def main():  # python -m credobot.rag.index
    # build, print counts per collection, run sample query "How is EMI calculated?"
    # against both collections (top-3 doc_id + distance), write transcripts/part1_index.md
```
Pass embeddings explicitly (`embedding_function=None`) so Chroma never tries to download
its own default ONNX model.

## Tests
`tests/test_chunking.py`
- `test_fixed_overlap` — consecutive fixed chunks of a 600-char text share ≥ `overlap`−20
  characters (verify via suffix/prefix overlap).
- `test_fixed_covers_text` — concatenating chunks (de-overlapped) contains every word.
- `test_sentence_grouping` — 5 sentences, n=2 → 3 chunks with 2,2,1 sentences.
- `test_chunk_ids_stable` — same input → same ids.
- `test_invalid_overlap_raises`.

`tests/test_index.py` (use `isolated_env`; mark `@pytest.mark.slow` is fine but keep in default run)
- `test_build_index_two_collections` — both collections exist, counts > 0, counts differ.
- `test_upsert_idempotent` — building twice keeps the same counts.
- `test_sample_query_sensible` — for "How is EMI calculated?" top-1 metadata `doc_id ==
  "emi_calculation"` in BOTH collections.
- `test_add_document` — adding a new doc increases both counts and is retrievable.

## Steps
- [ ] Implement `chunking.py` + tests
- [ ] Implement `embeddings.py`
- [ ] Implement `index.py` (`build_index`, `add_document`, `ensure_index`, `main`)
- [ ] Write `tests/test_index.py`
- [ ] Run Verify; record params/counts; update PROGRESS; commit

## Verify
1. `uv run python -m credobot.rag.index` → prints counts for `kb_fixed` and `kb_sentence`
   and the sample query top-3 for both, first hit `emi_calculation` in both.
2. Re-run with `HF_HUB_OFFLINE=1` (PowerShell: `$env:HF_HUB_OFFLINE="1"`) → still works.
3. `uv run pytest tests/test_chunking.py tests/test_index.py -q` → pass.

## Record in DECISIONS.md
`embed_model`, `fixed_chunk_params`, `sentence_chunk_params`, `chunk_counts`.

## Pitfalls
- Chroma default distance is L2; you must set `{"hnsw:space": "cosine"}` at creation.
  If you change it, delete `.chroma/` (metadata is fixed at creation).
- Windows: Chroma keeps file handles open; tests must use `tmp_path` dirs and not reuse
  the repo `.chroma/`.
- Don't let Chroma embed text itself (it would download a model) — always pass embeddings.

## Commit
`plan 03: fixed and sentence chunking indexed into two Chroma collections`
