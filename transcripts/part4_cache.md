# Part 4 — Response Caching Performance

- Generated: 2026-11-08T10:38:29.895549+00:00
- MOCK_LLM: True
- CREWAI_DISABLE_TELEMETRY: true
- OTEL_SDK_DISABLED: true

## Cache Architecture & Key Normalization

CredoBot wraps grounded retrieval with an in-memory thread-safe LRU response cache. Keys are normalized via Unicode NFKC, casefolding, and whitespace/punctuation stripping, enabling syntactic variants to resolve to identical cache entries without redundant vector search.

| Metric / Field | Call 1 (Cold Query) | Call 2 (Repeated Normalized Query) |
| --- | --- | --- |
| Raw Input Query | What is the penalty for prepaying a home loan? |   what is the PENALTY for prepaying a home loan?  |
| Normalized Cache Key | kb_fixed::what is the penalty for prepaying a home loan | kb_fixed::what is the penalty for prepaying a home loan |
| Cache Outcome | MISS | HIT |
| Execution Latency | 97.62 ms | 0.04 ms |
| Chroma Query Calls | 1 | 0 |
| LLM Generation Steps | 1 | 0 |
| Answers Identical | N/A | YES (Exact Match) |

## Cache Telemetry Summary

Final Cache Stats: `{'hits': 1, 'misses': 1, 'size': 1, 'max_entries': 512}`
