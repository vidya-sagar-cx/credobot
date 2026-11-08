# Part 3 — FastAPI Service & Structured JSON-Lines Logging

- Generated: 2026-11-08T10:12:40.016492+00:00
- MOCK_LLM: True
- CREWAI_DISABLE_TELEMETRY: true
- OTEL_SDK_DISABLED: true

Demonstration of the production FastAPI backend: HTTP endpoints (`POST /ask`, `POST /add-document`, `GET /health`), a disconnect-resilient multi-turn WebSocket endpoint (`/ws/chat`), and append-only structured JSON-Lines logging with trace IDs and zero raw PII.

## 1. Standard Policy Request (`POST /ask`)

- **HTTP Status:** `200`

- **X-Trace-Id Header:** `547a75b5a6114c7a9c1d4e0b7061dea0`

### Response JSON Excerpt

```json
{
  "trace_id": "547a75b5a6114c7a9c1d4e0b7061dea0",
  "response": {
    "answer": "card, passport, voter identity card, or driving licence. Customers must also provide one officially valid document as verified proof of identity and current residential address, such as an Aadhaar card, passport, voter identity card, or driving licence.",
    "intent": "policy",
    "sources": [
      "kyc_documents"
    ],
    "record": null,
    "escalate": false,
    "grounded": true,
    "top_similarity": 0.4085,
    "guardrail_events": []
  },
  "review": {
    "approved": true,
    "final_answer": "card, passport, voter identity card, or driving licence. Customers must also provide one officially valid document as verified proof of identity and current residential address, such as an Aadhaar card, passport, voter identity card, or driving licence.",
    "reason": "All claims supported by context."
  },
  "cache_hit": true,
  "events": [],
  "duration_ms": 214.35
}
```

## 2. PII Masking & Log Defense-in-Depth (`POST /ask`)

- **HTTP Status:** `200`

- **X-Trace-Id Header:** `cdf28878f5f0487fb3d3ff91797a2520`

- **Raw PII Absence in requests.jsonl:** `CONFIRMED (Zero Leakage)`

### JSONL Log Entry for PII Request

```json
{
  "@timestamp": "2026-11-08T10:12:38.856828+00:00",
  "level": "INFO",
  "service": "credobot-api",
  "trace_id": "cdf28878f5f0487fb3d3ff91797a2520",
  "event": "http_request",
  "method": "POST",
  "path": "/ask",
  "status_code": 200,
  "duration_ms": 441.68,
  "error": null,
  "session_id": null,
  "query_masked": "My PAN is [PAN_MASKED], Aadhaar is [AADHAAR_MASKED], and account is [ACCOUNT_MASKED]. Can I prepay my loan LA-1001 without penalty?",
  "cache_hit": false,
  "guardrail_events": [
    "pii_masked:PAN",
    "pii_masked:AADHAAR",
    "pii_masked:ACCOUNT"
  ],
  "intent": "mixed",
  "approved": false
}
```

## 3. Token & Cost Budget Rejection (`POST /ask` -> 413)

- **HTTP Status:** `413 (Payload Too Large)`

### 413 Error Response Body

```json
{
  "trace_id": "aeeabfa6be6448c1bf5224c9173828ae",
  "error": "budget_exceeded",
  "detail": {
    "query_chars": 12000,
    "input_tokens": 4250,
    "context_tokens": 150,
    "output_tokens": 500,
    "total_tokens": 4900,
    "cost_usd": 0.00294,
    "limit_tokens": 6000,
    "limit_cost_usd": 0.01,
    "limit_chars": 4000
  }
}
```

## 4. Dynamic Document Ingestion (`POST /add-document`)

- **Add Document Status:** `200`

```json
{
  "trace_id": "6536ba6505be423c887a78d340cb7fbc",
  "doc_id": "branch_hours",
  "chunks_added": {
    "kb_fixed": 64,
    "kb_sentence": 27
  }
}
```

- **Querying Ingested Document Status:** `200`

- **Answer Sources:** `['branch_hours', 'minimum_balance']`

> X Corp Bank branch customer service counters operate from 09:30 AM to 04:30 PM on all weekdays. 7:00 PM on the first and third Thursday of every month for mortgage consultations.

## 5. WebSocket Multi-Turn Chat & Abrupt Disconnect Recovery (`/ws/chat`)

### WebSocket Turn 1 (Client 1)

- **Turn:** 1 | **Trace ID:** `1145d05803764f7682e273e38f418405`

> Application LA-1007 (Education Loan, ₹3,133,000) is Approved.

### WebSocket Turn 2 (Client 1 - Coreference Follow-up)

- **Turn:** 2 | **Trace ID:** `c0ab49238be24cf6bec74bc08eae3432`

> Application LA-1007 (Education Loan, ₹3,133,000) is Approved.

- **Client 1 Disconnected:** `Abrupt socket closure verified`

### WebSocket Client 2 (Post-Disconnect Verification)

- **Status:** `Server healthy and responding after abrupt client disconnect`

- **Turn:** 1 | **Trace ID:** `d90815bd59d04b6ba6c16c56c214e2a0`

> Customers must also provide one officially valid document as verified proof of identity and current residential address, such as an Aadhaar card, passport, voter identity card, or driving licence. card, passport, voter identity card, or driving licence.

- **Health Check Post-Disconnect:** `{'status': 'ok', 'mock_llm': True, 'collections': {'kb_fixed': 64, 'kb_sentence': 27}, 'cache': {'hits': 3, 'misses': 9}}`

## 6. Structured JSON-Lines Log Tail (`logs/requests.jsonl`)

### Log Record #1

```json
{
  "@timestamp": "2026-11-08T10:12:39.643849+00:00",
  "level": "INFO",
  "service": "credobot-api",
  "trace_id": "c0ab49238be24cf6bec74bc08eae3432",
  "event": "ws_message",
  "session_id": "ws-demo-session",
  "turn": 2,
  "duration_ms": 227.0,
  "query_masked": "What is its loan amount and is it escalated?",
  "cache_hit": false,
  "guardrail_events": [],
  "intent": "status",
  "approved": true
}
```

### Log Record #2

```json
{
  "@timestamp": "2026-11-08T10:12:39.645849+00:00",
  "level": "INFO",
  "service": "credobot-api",
  "trace_id": "",
  "event": "ws_disconnect",
  "session_id": "ws-demo-session",
  "code": 1000
}
```

### Log Record #3

```json
{
  "@timestamp": "2026-11-08T10:12:39.986021+00:00",
  "level": "INFO",
  "service": "credobot-api",
  "trace_id": "d90815bd59d04b6ba6c16c56c214e2a0",
  "event": "ws_message",
  "session_id": "ws-client2",
  "turn": 1,
  "duration_ms": 335.14,
  "query_masked": "What documents are required for KYC?",
  "cache_hit": false,
  "guardrail_events": [],
  "intent": "policy",
  "approved": true
}
```

### Log Record #4

```json
{
  "@timestamp": "2026-11-08T10:12:39.988258+00:00",
  "level": "INFO",
  "service": "credobot-api",
  "trace_id": "",
  "event": "ws_disconnect",
  "session_id": "ws-client2",
  "code": 1000
}
```

### Log Record #5

```json
{
  "@timestamp": "2026-11-08T10:12:39.999339+00:00",
  "level": "INFO",
  "service": "credobot-api",
  "trace_id": "eb83773f11014cd6b8c784006fd713fa",
  "event": "http_request",
  "method": "GET",
  "path": "/health",
  "status_code": 200,
  "duration_ms": 5.69,
  "error": null
}
```
