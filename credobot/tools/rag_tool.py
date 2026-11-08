"""RAG tool callable for agent workflows."""
import json
from credobot import config, counters
from credobot.cache import cached_grounded_answer


def rag_lookup(query: str) -> str:
    """Execute grounded retrieval and return structured JSON result string."""
    counters.incr("tool.rag_lookup")
    ans, cache_hit = cached_grounded_answer(query, collection=config.DEPLOY_COLLECTION)
    payload = {
        "answer": ans.answer,
        "sources": ans.sources,
        "grounded": ans.grounded,
        "fallback": ans.fallback,
        "top_similarity": ans.top_similarity,
        "cache_hit": cache_hit,
        "context": [
            {
                "chunk_id": getattr(h, "chunk_id", ""),
                "doc_id": getattr(h, "doc_id", ""),
                "text": getattr(h, "text", str(h)),
                "similarity": getattr(h, "similarity", 0.0),
            }
            for h in ans.context
        ],
    }
    return json.dumps(payload)
