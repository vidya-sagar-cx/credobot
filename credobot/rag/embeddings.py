"""Embedding generation using local SentenceTransformers model."""
from functools import lru_cache
from credobot import config


@lru_cache(maxsize=1)
def get_model():
    """Lazily load SentenceTransformer model on CPU."""
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(config.EMBED_MODEL, device="cpu")


def embed(texts: list[str]) -> list[list[float]]:
    """Encode a list of texts into normalized embedding vectors."""
    if not texts:
        return []
    model = get_model()
    embeddings = model.encode(
        texts,
        normalize_embeddings=True,
        convert_to_numpy=True,
    )
    return embeddings.tolist()

