# Part 3 — FastAPI Service & Structured JSON-Lines Logging

- Generated: 2026-11-08T10:38:33.951109+00:00
- MOCK_LLM: True
- CREWAI_DISABLE_TELEMETRY: true
- OTEL_SDK_DISABLED: true

Demonstration of the production FastAPI backend: HTTP endpoints (`POST /ask`, `POST /add-document`, `GET /health`), a disconnect-resilient multi-turn WebSocket endpoint (`/ws/chat`), and append-only structured JSON-Lines logging with trace IDs and zero raw PII.

## 1. Standard Policy Request (`POST /ask`)

- **HTTP Status:** `200`

- **X-Trace-Id Header:** `be0ead3267b84ac7a8e7690f6d11d8c6`

### Response JSON Excerpt

```json
{
  "trace_id": "be0ead3267b84ac7a8e7690f6d11d8c6",
  "response": {
    "answer": "Customers must also provide one officially valid document as verified proof of identity and current residential address, such as an Aadhaar card, passport, voter identity card, or driving licence. assport, voter identity card, or driving licence.",
    "intent": "policy",
    "sources": [
      "kyc_documents"
    ],
    "record": null,
    "escalate": false,
    "grounded": true,
    "top_similarity": 0.4565,
    "guardrail_events": []
  },
  "review": {
    "approved": true,
    "final_answer": "Customers must also provide one officially valid document as verified proof of identity and current residential address, such as an Aadhaar card, passport, voter identity card, or driving licence. assport, voter identity card, or driving licence.",
    "reason": "All claims supported by context."
  },
  "cache_hit": true,
  "events": [],
  "duration_ms": 188.3
}
```

## 2. PII Masking & Log Defense-in-Depth (`POST /ask`)

- **HTTP Status:** `200`

- **X-Trace-Id Header:** `d13f4020a6b44a22b9cff3851c849ed8`

- **Raw PII Absence in requests.jsonl:** `CONFIRMED (Zero Leakage)`

### JSONL Log Entry for PII Request

```json
{
  "@timestamp": "2026-11-08T10:38:32.599845+00:00",
  "level": "INFO",
  "service": "credobot-api",
  "trace_id": "d13f4020a6b44a22b9cff3851c849ed8",
  "event": "http_request",
  "method": "POST",
  "path": "/ask",
  "status_code": 200,
  "duration_ms": 333.27,
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
  "trace_id": "36a9aef80521424d93fa77b4b818af1a",
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
  "trace_id": "cb3932578a344a2bbda742698668f2b6",
  "doc_id": "branch_hours",
  "chunks_added": {
    "kb_fixed": 63,
    "kb_sentence": 27
  }
}
```

- **Querying Ingested Document Status:** `200`

- **Answer Sources:** `['branch_hours', 'kyc_documents']`

> CRED branch customer service counters operate from 09:30 AM to 04:30 PM on all weekdays. on the first and third Thursday of every month for mortgage consultations.

## 5. WebSocket Multi-Turn Chat & Abrupt Disconnect Recovery (`/ws/chat`)

### WebSocket Turn 1 (Client 1)

- **Turn:** 1 | **Trace ID:** `aa0a013c14e9476e83ceab91630be5f3`

> Application LA-1007 (Education Loan, ₹3,133,000) is Approved.

### WebSocket Turn 2 (Client 1 - Coreference Follow-up)

- **Turn:** 2 | **Trace ID:** `926cc8e6bbbe4325adbd0d6718ae3f87`

> Application LA-1007 (Education Loan, ₹3,133,000) is Approved.

- **Client 1 Disconnected:** `Abrupt socket closure verified`

### WebSocket Client 2 (Post-Disconnect Verification)

- **Status:** `Server healthy and responding after abrupt client disconnect`

- **Turn:** 1 | **Trace ID:** `e5a08d24d3e441329dc9b8b0688037e2`

> Customers must also provide one officially valid document as verified proof of identity and current residential address, such as an Aadhaar card, passport, voter identity card, or driving licence. Under regulatory compliance standards, re-KYC profile reviews are mandatorily scheduled every two years for high-risk customers, every eight

- **Health Check Post-Disconnect:** `{'status': 'ok', 'mock_llm': True, 'collections': {'kb_fixed': 63, 'kb_sentence': 27}, 'cache': {'hits': 3, 'misses': 9}}`

## 6. Structured JSON-Lines Log Tail (`logs/requests.jsonl`)

### Log Record #1

```json
{
  "@timestamp": "2026-11-08T10:38:33.589981+00:00",
  "level": "INFO",
  "service": "credobot-api",
  "trace_id": "926cc8e6bbbe4325adbd0d6718ae3f87",
  "event": "ws_message",
  "session_id": "ws-demo-session",
  "turn": 2,
  "duration_ms": 285.15,
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
  "@timestamp": "2026-11-08T10:38:33.592196+00:00",
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
  "@timestamp": "2026-11-08T10:38:33.926597+00:00",
  "level": "INFO",
  "service": "credobot-api",
  "trace_id": "e5a08d24d3e441329dc9b8b0688037e2",
  "event": "ws_message",
  "session_id": "ws-client2",
  "turn": 1,
  "duration_ms": 328.68,
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
  "@timestamp": "2026-11-08T10:38:33.927602+00:00",
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
  "@timestamp": "2026-11-08T10:38:33.938542+00:00",
  "level": "INFO",
  "service": "credobot-api",
  "trace_id": "a146cb285e7541159d2270c9029834b9",
  "event": "http_request",
  "method": "GET",
  "path": "/health",
  "status_code": 200,
  "duration_ms": 5.84,
  "error": null
}
```
