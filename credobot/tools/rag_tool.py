"""RAG tool callable for agent workflows."""
import json
from credobot import config, counters
from credobot.rag.generate import grounded_answer


def rag_lookup(query: str) -> str:
    """Execute grounded retrieval and return structured JSON result string."""
    counters.incr("tool.rag_lookup")
    ans = grounded_answer(query, collection=config.DEPLOY_COLLECTION)
    payload = {
        "answer": ans.answer,
        "sources": ans.sources,
        "grounded": ans.grounded,
        "fallback": ans.fallback,
        "top_similarity": ans.top_similarity,
        "context": [h.text for h in ans.context],
    }
    return json.dumps(payload)
