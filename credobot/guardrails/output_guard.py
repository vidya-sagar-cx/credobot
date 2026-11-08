"""Output-side guardrails: sentence-level groundedness verification."""
from dataclasses import dataclass, field
import numpy as np

from credobot import config, counters
from credobot.rag.embeddings import embed
from credobot.rag.kb import split_sentences
from credobot.rag.retrieve import Hit

REFUSAL_UNGROUNDED: str = (
    "I can't answer that reliably from X Corp's policy documents, so I won't guess. "
    "Please contact lending operations."
)


@dataclass
class SentenceSupport:
    sentence: str
    best_similarity: float
    supported: bool


def sentence_support(
    answer: str,
    context_texts: list[str],
    threshold: float | None = None,
) -> list[SentenceSupport]:
    """Measure sentence-level semantic support against context texts.

    Each answer sentence is checked:
    1. Exact substring presence in any context text yields similarity 1.0.
    2. Otherwise, cosine similarity (dot product of normalized embeddings)
       is computed against all context sentences, taking the maximum.
    """
    threshold = threshold if threshold is not None else getattr(config, "SUPPORT_THRESHOLD", 0.70)
    ans_sentences = split_sentences(answer)
    if not ans_sentences:
        return []

    # Flatten context texts into individual sentences
    ctx_sentences: list[str] = []
    for ct in context_texts:
        ctx_sentences.extend(split_sentences(ct))

    # Pre-embed context sentences if available
    ctx_embeddings = (
        np.asarray(embed(ctx_sentences)) if ctx_sentences else np.empty((0, 384))
    )

    results: list[SentenceSupport] = []
    for s in ans_sentences:
        # Check exact verbatim substring match
        clean_s = s.strip()
        if any(clean_s in ct for ct in context_texts) or any(
            clean_s in cs for cs in ctx_sentences
        ):
            results.append(
                SentenceSupport(sentence=s, best_similarity=1.0, supported=True)
            )
            continue

        if len(ctx_sentences) == 0:
            results.append(
                SentenceSupport(sentence=s, best_similarity=0.0, supported=False)
            )
            continue

        s_vec = np.asarray(embed([s])[0])  # shape (384,)
        # Cosine similarity via dot product (embeddings are already L2 normalized)
        sims = np.dot(ctx_embeddings, s_vec)
        best_sim = float(np.max(sims))
        is_supp = best_sim >= threshold
        results.append(
            SentenceSupport(
                sentence=s,
                best_similarity=best_sim,
                supported=is_supp,
            )
        )

    return results


@dataclass
class GroundingCheck:
    grounded: bool
    reason: str
    top_similarity: float
    unsupported: list[str] = field(default_factory=list)


def check_grounded(
    answer: str,
    hits: list[Hit],
    *,
    is_status_only: bool = False,
    threshold: float | None = None,
) -> GroundingCheck:
    """Validate that an answer is fully supported by retrieved context hits."""
    if is_status_only:
        return GroundingCheck(
            grounded=True,
            reason="status_only",
            top_similarity=1.0,
            unsupported=[],
        )

    top_sim = hits[0].similarity if hits else 0.0

    # Gate (a): IDK Threshold gate
    if not hits or top_sim < config.IDK_THRESHOLD:
        counters.incr("guardrails.groundedness_refused")
        return GroundingCheck(
            grounded=False,
            reason="low_retrieval_similarity",
            top_similarity=top_sim,
            unsupported=[answer],
        )

    # Gate (b): Sentence support check
    context_texts = [h.text for h in hits]
    supports = sentence_support(answer, context_texts, threshold=threshold)
    unsupported = [s.sentence for s in supports if not s.supported]

    if unsupported:
        counters.incr("guardrails.groundedness_refused")
        return GroundingCheck(
            grounded=False,
            reason="unsupported_claim",
            top_similarity=top_sim,
            unsupported=unsupported,
        )

    return GroundingCheck(
        grounded=True,
        reason="supported",
        top_similarity=top_sim,
        unsupported=[],
    )


def calibrate_support_threshold() -> tuple[float, float, float]:
    """Measure similarity distribution of genuine vs fabricated claims to calibrate SUPPORT_THRESHOLD."""
    from credobot.guardrails.fixtures import UNSUPPORTED_CLAIMS
    from credobot.rag.queries import IN_SCOPE
    from credobot.rag.retrieve import retrieve

    print("Measuring genuine supported answers...")
    genuine_sims: list[float] = []
    for query, _ in IN_SCOPE:
        hits = retrieve(query, collection=config.DEPLOY_COLLECTION, k=3)
        context_texts = [h.text for h in hits]
        # In mock mode, answers are extractive chunks
        extracted = hits[0].text if hits else ""
        supports = sentence_support(extracted, context_texts, threshold=0.0)
        for s in supports:
            genuine_sims.append(s.best_similarity)

    print(f"Genuine answers min similarity: {min(genuine_sims):.4f}")

    print("Measuring fabricated unsupported claims across all deployed contexts...")
    from credobot.rag.index import get_collection
    coll = get_collection(config.DEPLOY_COLLECTION)
    all_docs = coll.get()["documents"]

    unsupported_sims: list[float] = []
    for claim in UNSUPPORTED_CLAIMS:
        # Check against the entire KB context pool
        supports = sentence_support(claim, all_docs, threshold=0.0)
        for s in supports:
            unsupported_sims.append(s.best_similarity)

    min_genuine = min(genuine_sims)
    max_unsupported = max(unsupported_sims)
    calibrated_midpoint = round((min_genuine + max_unsupported) / 2.0, 2)

    print(f"Supported cluster:   min = {min_genuine:.4f}, max = {max(genuine_sims):.4f}")
    print(f"Unsupported cluster: min = {min(unsupported_sims):.4f}, max = {max_unsupported:.4f}")
    print(f"Calibrated midpoint threshold: {calibrated_midpoint:.2f}")

    return min_genuine, max_unsupported, calibrated_midpoint


if __name__ == "__main__":
    calibrate_support_threshold()
