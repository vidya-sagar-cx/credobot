"""Grounded generation using retrieved context and calibrated threshold."""
from dataclasses import dataclass
from typing import Any
import numpy as np
from credobot import config, counters
from credobot.demos.transcript import Transcript
from credobot.rag.embeddings import embed
from credobot.rag.index import COLLECTIONS
from credobot.rag.kb import split_sentences
from credobot.rag.queries import IN_SCOPE, OUT_OF_SCOPE
from credobot.rag.retrieve import Hit, retrieve, top1_similarity

IDK_MESSAGE: str = (
    "I don't know — the CRED policy knowledge base doesn't cover that. "
    "Please contact lending operations."
)


@dataclass
class GroundedAnswer:
    query: str
    answer: str
    grounded: bool
    fallback: bool
    top_similarity: float
    sources: list[str]
    context: list[Hit]


def build_prompt(query: str, hits: list[Hit]) -> str:
    """Construct a constrained prompt for an LLM requiring grounded answers."""
    context_blocks = "\n\n".join(
        f"[{i+1}] (Source: {h.doc_id})\n{h.text}" for i, h in enumerate(hits)
    )
    return (
        "You are an assistant answering policy queries for CRED.\n"
        "Answer ONLY using the context below. If the context does not contain the answer, "
        f"reply exactly: '{IDK_MESSAGE}'.\n\n"
        f"Context:\n{context_blocks}\n\n"
        f"Question: {query}\nAnswer:"
    )


def _mock_generate(query: str, hits: list[Hit], max_sentences: int = 2) -> str:
    """Extractive generation: select most relevant sentences from hits in original order."""
    ordered_sentences: list[str] = []
    seen: set[str] = set()

    for h in hits:
        for s in split_sentences(h.text):
            if s not in seen:
                seen.add(s)
                ordered_sentences.append(s)

    if not ordered_sentences:
        return IDK_MESSAGE

    q_vec = np.array(embed([query])[0])
    s_vecs = np.array(embed(ordered_sentences))

    # Dot product on unit-normalized vectors gives cosine similarity
    sims = np.dot(s_vecs, q_vec)

    # Pick top sentence indices
    top_indices = np.argsort(sims)[::-1][:max_sentences]
    # Re-order by their original appearance order for coherence
    sorted_top = sorted(top_indices)
    picked_sentences = [ordered_sentences[idx] for idx in sorted_top]

    return " ".join(picked_sentences)


def grounded_answer(
    query: str,
    collection: str | None = None,
    k: int = config.TOP_K,
    client: Any = None,
) -> GroundedAnswer:
    """Generate an answer grounded strictly in retrieved knowledge base chunks."""
    target_coll = collection or config.DEPLOY_COLLECTION or COLLECTIONS["sentence"]
    hits = retrieve(query, collection=target_coll, k=k, client=client)

    top_sim = top1_similarity(hits)
    threshold = config.IDK_THRESHOLD if config.IDK_THRESHOLD is not None else 0.29

    if not hits or top_sim < threshold:
        return GroundedAnswer(
            query=query,
            answer=IDK_MESSAGE,
            grounded=False,
            fallback=True,
            top_similarity=top_sim,
            sources=[],
            context=hits,
        )

    counters.incr("llm.generate")

    if config.MOCK_LLM:
        answer_text = _mock_generate(query, hits)
    else:
        try:
            from credobot.llm import factory

            text_llm = factory.get_text_llm()
            prompt = build_prompt(query, hits)
            answer_text = text_llm(prompt)
        except Exception:
            answer_text = _mock_generate(query, hits)

    sources = sorted({h.doc_id for h in hits})
    return GroundedAnswer(
        query=query,
        answer=answer_text,
        grounded=True,
        fallback=False,
        top_similarity=top_sim,
        sources=sources,
        context=hits,
    )


def main() -> int:
    """Demonstrate grounded generation across in-scope queries and an out-of-scope query."""
    test_queries = [q for q, _ in IN_SCOPE] + [OUT_OF_SCOPE[0]]
    results: list[GroundedAnswer] = []

    print("=" * 70)
    print("GROUNDED GENERATION DEMO")
    print(f"Active Threshold (IDK_THRESHOLD): {config.IDK_THRESHOLD}")
    print("=" * 70)

    transcript_rows = []

    for q in test_queries:
        # Retrieve from both to show similarity comparison
        hits_fixed = retrieve(q, collection=COLLECTIONS["fixed"])
        sim_fixed = top1_similarity(hits_fixed)

        ans = grounded_answer(q, collection=COLLECTIONS["sentence"])
        results.append(ans)

        print(f"\nQuery: '{q}'")
        print(f"Top-1 Sim: sent={ans.top_similarity:.4f}, fixed={sim_fixed:.4f}")
        print(f"Fallback Triggered: {ans.fallback}")
        print(f"Sources: {ans.sources}")
        print(f"Answer: {ans.answer}")

        transcript_rows.append(
            [
                q,
                f"{ans.top_similarity:.4f}",
                f"{sim_fixed:.4f}",
                str(ans.fallback),
                ", ".join(ans.sources) if ans.sources else "None",
                ans.answer,
            ]
        )

    t = Transcript("part1_grounded", "Part 1 — Grounded Generation Demo")
    t.h2("Grounded Generation Results (≥5 In-Scope + 1 Out-Of-Scope)")
    t.table(
        ["Query", "Sentence Top-1", "Fixed Top-1", "Fallback?", "Sources", "Answer"],
        transcript_rows,
    )
    saved = t.save()
    print(f"\nTranscript written to: {saved}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
