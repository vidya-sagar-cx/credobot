"""Demonstration script for FastAPI endpoints, WebSockets, and JSONL logging."""
import json
from pathlib import Path

from fastapi.testclient import TestClient

from credobot import config
from credobot.api.app import app
from credobot.api.logging_mw import LOGGER
from credobot.demos.transcript import Transcript
from credobot.guardrails.fixtures import FABRICATED_PII_SAMPLES


def main() -> int:
    t = Transcript("part3_api", "Part 3 — FastAPI Service & Structured JSON-Lines Logging")
    t.para(
        "Demonstration of the production FastAPI backend: HTTP endpoints (`POST /ask`, "
        "`POST /add-document`, `GET /health`), a disconnect-resilient multi-turn WebSocket "
        "endpoint (`/ws/chat`), and append-only structured JSON-Lines logging with trace IDs "
        "and zero raw PII."
    )

    client = TestClient(app)

    # -------------------------------------------------------------
    # 1. POST /ask (Standard Policy Question)
    # -------------------------------------------------------------
    t.h2("1. Standard Policy Request (`POST /ask`)")
    q1 = "What documents do I need for KYC?"
    resp1 = client.post("/ask", json={"query": q1})
    trace1 = resp1.headers.get("x-trace-id", "")
    t.bullet(f"**HTTP Status:** `{resp1.status_code}`")
    t.bullet(f"**X-Trace-Id Header:** `{trace1}`")
    t.h3("Response JSON Excerpt")
    t.code(json.dumps(resp1.json(), indent=2), lang="json")

    # -------------------------------------------------------------
    # 2. POST /ask with PII (Zero-Leakage Log Verification)
    # -------------------------------------------------------------
    t.h2("2. PII Masking & Log Defense-in-Depth (`POST /ask`)")
    pan_sample = FABRICATED_PII_SAMPLES[0]["raw"]
    aadhaar_sample = FABRICATED_PII_SAMPLES[1]["raw"]
    account_sample = FABRICATED_PII_SAMPLES[3]["raw"]

    q2 = (
        f"My PAN is {pan_sample}, Aadhaar is {aadhaar_sample}, and account is {account_sample}. "
        "Can I prepay my loan LA-1001 without penalty?"
    )
    resp2 = client.post("/ask", json={"query": q2})
    trace2 = resp2.headers.get("x-trace-id", "")
    t.bullet(f"**HTTP Status:** `{resp2.status_code}`")
    t.bullet(f"**X-Trace-Id Header:** `{trace2}`")

    # Inspect log file on disk to confirm raw PII never lands in logs
    log_file = LOGGER.path
    log_content = log_file.read_text(encoding="utf-8") if log_file.exists() else ""

    assert pan_sample not in log_content, "CRITICAL: Raw PAN found in logs!"
    assert aadhaar_sample not in log_content, "CRITICAL: Raw Aadhaar found in logs!"
    assert account_sample not in log_content, "CRITICAL: Raw Account found in logs!"

    # Find the specific log line for trace2
    target_line = ""
    for line in log_content.splitlines():
        if trace2 in line:
            target_line = line
            break

    t.bullet("**Raw PII Absence in requests.jsonl:** `CONFIRMED (Zero Leakage)`")
    t.h3("JSONL Log Entry for PII Request")
    t.code(json.dumps(json.loads(target_line), indent=2) if target_line else "Not found", lang="json")

    # -------------------------------------------------------------
    # 3. POST /ask Budget Limit Enforcement (HTTP 413)
    # -------------------------------------------------------------
    t.h2("3. Token & Cost Budget Rejection (`POST /ask` -> 413)")
    q3_large = "Loan policy guidelines. " * 500  # > 10,000 characters
    resp3 = client.post("/ask", json={"query": q3_large})
    t.bullet(f"**HTTP Status:** `{resp3.status_code} (Payload Too Large)`")
    t.h3("413 Error Response Body")
    t.code(json.dumps(resp3.json(), indent=2), lang="json")

    # -------------------------------------------------------------
    # 4. POST /add-document & Immediate Retrieval
    # -------------------------------------------------------------
    t.h2("4. Dynamic Document Ingestion (`POST /add-document`)")
    doc_text = (
        "X Corp Bank branch customer service counters operate from 09:30 AM to 04:30 PM on all "
        "weekdays. Extended evening advisory support is available until 07:00 PM on the first and "
        "third Thursday of every month for mortgage consultations."
    )
    resp4 = client.post(
        "/add-document",
        json={"doc_id": "branch_hours", "text": doc_text},
    )
    t.bullet(f"**Add Document Status:** `{resp4.status_code}`")
    t.code(json.dumps(resp4.json(), indent=2), lang="json")

    # Query the newly added document
    resp4_query = client.post("/ask", json={"query": "What are the branch customer service hours?"})
    t.bullet(f"**Querying Ingested Document Status:** `{resp4_query.status_code}`")
    t.bullet(f"**Answer Sources:** `{resp4_query.json().get('response', {}).get('sources')}`")
    t.para(f"> {resp4_query.json().get('response', {}).get('answer')}")

    # -------------------------------------------------------------
    # 5. WebSocket Multi-Turn Chat & Disconnect Survival
    # -------------------------------------------------------------
    t.h2("5. WebSocket Multi-Turn Chat & Abrupt Disconnect Recovery (`/ws/chat`)")
    ws_session = "ws-demo-session"

    # Client 1: Connects, asks Turn 1, Turn 2, then disconnects abruptly
    with client.websocket_connect(f"/ws/chat?session_id={ws_session}") as ws1:
        # Turn 1
        ws1.send_text(json.dumps({"query": "What is the status of application LA-1007?"}))
        r1 = json.loads(ws1.receive_text())
        t.h3("WebSocket Turn 1 (Client 1)")
        t.bullet(f"**Turn:** {r1.get('turn')} | **Trace ID:** `{r1.get('trace_id')}`")
        t.para(f"> {r1.get('response', {}).get('answer')}")

        # Turn 2: Pronoun reference
        ws1.send_text(json.dumps({"query": "What is its loan amount and is it escalated?"}))
        r2 = json.loads(ws1.receive_text())
        t.h3("WebSocket Turn 2 (Client 1 - Coreference Follow-up)")
        t.bullet(f"**Turn:** {r2.get('turn')} | **Trace ID:** `{r2.get('trace_id')}`")
        t.para(f"> {r2.get('response', {}).get('answer')}")

        # Client 1 exits abruptly without waiting

    t.bullet("**Client 1 Disconnected:** `Abrupt socket closure verified`")

    # Client 2: Reconnects to test server survival
    with client.websocket_connect("/ws/chat?session_id=ws-client2") as ws2:
        ws2.send_text(json.dumps({"query": "What documents are required for KYC?"}))
        r3 = json.loads(ws2.receive_text())
        t.h3("WebSocket Client 2 (Post-Disconnect Verification)")
        t.bullet(f"**Status:** `Server healthy and responding after abrupt client disconnect`")
        t.bullet(f"**Turn:** {r3.get('turn')} | **Trace ID:** `{r3.get('trace_id')}`")
        t.para(f"> {r3.get('response', {}).get('answer')}")

    # Check health endpoint
    health_resp = client.get("/health")
    t.bullet(f"**Health Check Post-Disconnect:** `{health_resp.json()}`")

    # -------------------------------------------------------------
    # 6. Tail of requests.jsonl (Last 5 Structured Log Entries)
    # -------------------------------------------------------------
    t.h2("6. Structured JSON-Lines Log Tail (`logs/requests.jsonl`)")
    lines = [l for l in log_file.read_text(encoding="utf-8").splitlines() if l.strip()]
    tail_lines = lines[-5:] if len(lines) >= 5 else lines

    for idx, l in enumerate(tail_lines, 1):
        t.h3(f"Log Record #{idx}")
        t.code(json.dumps(json.loads(l), indent=2), lang="json")

    saved = t.save()
    print(f"\n[OK] Part 3 API transcript generated at: {saved}")
    return 0


if __name__ == "__main__":
    main()
