# Part 3 — FastAPI Service & Structured JSON-Lines Logging

- Generated: 2026-11-08T09:57:24.892702+00:00
- MOCK_LLM: True
- CREWAI_DISABLE_TELEMETRY: true
- OTEL_SDK_DISABLED: true

Demonstration of the production FastAPI backend: HTTP endpoints (`POST /ask`, `POST /add-document`, `GET /health`), a disconnect-resilient multi-turn WebSocket endpoint (`/ws/chat`), and append-only structured JSON-Lines logging with trace IDs and zero raw PII.

## 1. Standard Policy Request (`POST /ask`)

- **HTTP Status:** `200`

- **X-Trace-Id Header:** `25501d2a980e4484bcd3382fef00edcd`

### Response JSON Excerpt

```json
{
  "trace_id": "25501d2a980e4484bcd3382fef00edcd",
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
  "cache_hit": false,
  "events": [],
  "duration_ms": 11011.75
}
```

## 2. PII Masking & Log Defense-in-Depth (`POST /ask`)

- **HTTP Status:** `200`

- **X-Trace-Id Header:** `00c16ee258a14dc7acbb3565d512288e`

- **Raw PII Absence in requests.jsonl:** `CONFIRMED (Zero Leakage)`

### JSONL Log Entry for PII Request

```json
{
  "@timestamp": "2026-11-08T09:57:23.574010+00:00",
  "level": "INFO",
  "service": "credobot-api",
  "trace_id": "00c16ee258a14dc7acbb3565d512288e",
  "event": "http_request",
  "method": "POST",
  "path": "/ask",
  "status_code": 200,
  "duration_ms": 382.52,
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
  "trace_id": "8361a37864894551b3e20834214b11c9",
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
  "trace_id": "fe987792778b40579171efba4a126de0",
  "doc_id": "branch_hours",
  "chunks_added": {
    "kb_fixed": 66,
    "kb_sentence": 29
  }
}
```

- **Querying Ingested Document Status:** `200`

- **Answer Sources:** `['branch_hours', 'minimum_balance']`

> X Corp Bank branch customer service counters operate from 09:30 AM to 04:30 PM on all weekdays. 7:00 PM on the first and third Thursday of every month for mortgage consultations.

## 5. WebSocket Multi-Turn Chat & Abrupt Disconnect Recovery (`/ws/chat`)

### WebSocket Turn 1 (Client 1)

- **Turn:** 1 | **Trace ID:** `26a0cf28a8794e2882cff87b3137de80`

> Application LA-1007 (Education Loan, ₹3,133,000) is Approved.

### WebSocket Turn 2 (Client 1 - Coreference Follow-up)

- **Turn:** 2 | **Trace ID:** `4d08a264bfcc45e68b2b24afb2a4104e`

> Application LA-1007 (Education Loan, ₹3,133,000) is Approved.

- **Client 1 Disconnected:** `Abrupt socket closure verified`

### WebSocket Client 2 (Post-Disconnect Verification)

- **Status:** `Server healthy and responding after abrupt client disconnect`

- **Turn:** 1 | **Trace ID:** `22eeef141921424f9cbaa362456db1a7`

> Customers must also provide one officially valid document as verified proof of identity and current residential address, such as an Aadhaar card, passport, voter identity card, or driving licence. card, passport, voter identity card, or driving licence.

- **Health Check Post-Disconnect:** `{'status': 'ok', 'mock_llm': True, 'collections': {'kb_fixed': 66, 'kb_sentence': 29}, 'cache': {'hits': 0, 'misses': 6}}`

## 6. Structured JSON-Lines Log Tail (`logs/requests.jsonl`)

### Log Record #1

```json
{
  "@timestamp": "2026-11-08T09:57:24.500293+00:00",
  "level": "INFO",
  "service": "credobot-api",
  "trace_id": "4d08a264bfcc45e68b2b24afb2a4104e",
  "event": "ws_message",
  "session_id": "ws-demo-session",
  "turn": 2,
  "duration_ms": 223.47,
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
  "@timestamp": "2026-11-08T09:57:24.501289+00:00",
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
  "@timestamp": "2026-11-08T09:57:24.854804+00:00",
  "level": "INFO",
  "service": "credobot-api",
  "trace_id": "22eeef141921424f9cbaa362456db1a7",
  "event": "ws_message",
  "session_id": "ws-client2",
  "turn": 1,
  "duration_ms": 347.78,
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
  "@timestamp": "2026-11-08T09:57:24.856803+00:00",
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
  "@timestamp": "2026-11-08T09:57:24.871810+00:00",
  "level": "INFO",
  "service": "credobot-api",
  "trace_id": "e43163ccd0234993a1b086b6516bdd0d",
  "event": "http_request",
  "method": "GET",
  "path": "/health",
  "status_code": 200,
  "duration_ms": 9.09,
  "error": null
}
```
