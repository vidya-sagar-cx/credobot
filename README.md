# CredoBot: Banking & FinTech Loan-Support Agent

**Track: Finance (Banking & FinTech)**

CredoBot is an enterprise-grade loan-support agent built for CRED's lending-operations team. It answers complex retail banking loan-policy queries, inspects loan application records with an empirical escalation formula, maintains conversation context across turns, defends against adversarial prompts and PII leakage, validates every generated draft through an independent multi-agent review team, and enforces a multi-layered AI governance framework.

### Architecture Overview
The runtime operates as a 7-stage pipeline (detailed in [`architecture.md`](architecture.md) with complete Mermaid flows):
1. **Request Budget & Governance Gate:** Checks estimated token count and dollar cost against configured ceilings (`max_request_tokens=6000`, `max_request_cost_usd=$0.01`); enforces tool Access Control Lists (least autonomy).
2. **Input Guardrails:** Detects and blocks adversarial prompt injections; redacts fixed-format PII (PAN, Aadhaar, Account numbers) with synthetic masks before model exposure.
3. **Session Memory:** Rehydrates conversation history via LangChain message stores; rewrites follow-up queries with antecedent context.
4. **Normalized Query Cache:** Checks in-memory LRU cache with NFKC normalization for instantaneous cache hits on repeated policy inquiries.
5. **CrewAI Agent Crew:** Sequential 3-agent orchestration (`RetrievalAgent` with RAG tool, `LookupAgent` with loan status tool, `ResponseComposerAgent` synthesizing final answers into validated `CrewResponse` schemas).
6. **Output Guardrails:** Validates groundedness against retrieved context via cosine entailment checks (`SUPPORT_THRESHOLD=0.81`), refusing ungrounded assertions.
7. **AutoGen Review Stage:** 2-agent `RoundRobinGroupChat` (`PolicyComplianceReviewer` and `FinalEditor`, `max_turns=2`) verifying factual consistency and outputting a validated `ReviewVerdict` (approving or revising the draft).
8. **Structured JSONL Audit Logging:** Writes single-line JSONL audit logs with unique trace IDs, execution durations, and masked PII.

> For visual diagrams, sequence flows, and component-by-component specifications, see [`architecture.md`](architecture.md).
> For onboarding, developer commands, and contribution rules, see [`CONTRIBUTING.md`](CONTRIBUTING.md).

---

## Zero-Network & Offline Execution Guarantee
CredoBot executes deterministically under `MOCK_LLM=true` with **zero external API keys and zero outbound network calls**:
- Embeddings (`sentence-transformers/all-MiniLM-L6-v2`) and vector search (`ChromaDB`) run 100% locally.
- CrewAI telemetry and OpenTelemetry network calls are explicitly disabled:
  ```bash
  CREWAI_DISABLE_TELEMETRY=true
  OTEL_SDK_DISABLED=true
  ```
  *(Configured as defaults in `credobot/config.py` and `.env.example`).*
- All graded demonstration transcripts in `transcripts/` are generated under `MOCK_LLM=true` and pass automated offline assertions (`network calls attempted: 0`).

---

## Quickstart

Follow [`docs/SETUP.md`](docs/SETUP.md) for platform-specific prerequisites (Windows, macOS, Linux).

```bash
# 1. Clone repository and navigate to folder
git clone https://github.com/your-org/credobot.git
cd credobot

# 2. Sync dependencies using uv
uv sync

# 3. Run full test suite (143+ unit and integration tests)
uv run pytest -q

# 4. Regenerate all transcripts with zero network calls
uv run python -m credobot.demos.run_all
```

---

## Part 1 — Dataset Design & RAG Core

### 1. Loan Application Dataset Design (`dataset.py`)
- **Seed:** `2026`
- **Total Records:** `60` (exceeds requirement `>=40`)
- **Category Weights:**
  - `Personal Loan`: `0.25` (25%)
  - `Home Loan`: `0.20` (20%)
  - `Auto Loan`: `0.20` (20%)
  - `Business Loan`: `0.20` (20%)
  - `Education Loan`: `0.15` (15%)
- **Status Weights:**
  - `Under Review`: `0.25` (25%)
  - `Submitted`: `0.20` (20%)
  - `Approved`: `0.20` (20%)
  - `Disbursed`: `0.20` (20%)
  - `Rejected`: `0.15` (15%)
- **Loan Amount Ranges & Rationale:**
  - `Personal Loan`: ₹50,000 – ₹2,500,000 (unsecured retail credit)
  - `Home Loan`: ₹1,000,000 – ₹15,000,000 (prime residential property financing)
  - `Auto Loan`: ₹200,000 – ₹3,000,000 (new passenger vehicle financing)
  - `Education Loan`: ₹100,000 – ₹4,000,000 (domestic/international higher education tuition)
  - `Business Loan`: ₹500,000 – ₹20,000,000 (MSME operational working capital and equipment)
  *Rationale:* Ranges mirror statutory limits and commercial practices of tier-1 Indian retail banks.
- **Fraud Probability & Distribution:**
  - Configured fraud draw: `0.18`
  - Realized fraud flag rate: `12 / 60` = **`20.0%`** (strictly within `10% – 30%` mandate)
- **Empirical Dataset Counts:**
  - *By Category:* `Personal Loan`: 22, `Auto Loan`: 12, `Home Loan`: 11, `Business Loan`: 9, `Education Loan`: 6 (all `>=3`)
  - *By Status:* `Under Review`: 22, `Approved`: 15, `Disbursed`: 10, `Rejected`: 7, `Submitted`: 6 (all `>=1`)
- **Reproduce Dataset Command:**
  ```bash
  uv run python dataset.py
  ```
  *See [`transcripts/part1_dataset.md`](transcripts/part1_dataset.md).*

### 2. Knowledge Base (`kb/*.md`)
Authored 13 comprehensive policy documents (`>=2-5 sentences each`) covering all required banking policy areas:
1. `loan_eligibility`: Minimum credit scores (720 home, 680 personal) and income floors.
2. `emi_calculation`: Reducing-balance amortization formula and monthly compounding.
3. `credit_card_fees`: Annual fees (₹1,500) and balance-tiered late charges.
4. `kyc_documents`: Mandatory PAN and officially valid identity documents (Aadhaar, Passport).
5. `fraud_dispute`: 3-day zero customer liability and shadow credit resolution.
6. `account_closure`: Digital application procedures, balance settlement, and ₹500 early closure fee.
7. `interest_rate_slabs`: Credit score tiers (>=750: 10.50%, 700-749: 12.00%, <700: 14.50%).
8. `prepayment_penalty`: Nil penalty on floating-rate retail loans; 2% on fixed-rate commercial prepayments.
9. `minimum_balance`: Average monthly balance (₹10,000 metro, ₹5,000 urban, ₹2,000 semi-urban).
10. `credit_score_factors`: Weightings (35% payment history, 30% utilization, 15% duration, 10% mix, 10% inquiries).
11. `joint_accounts`: Up to 4 holders with Either-or-Survivor, Joint, or Former-or-Survivor mandates.
12. `nri_accounts`: NRE, NRO, and FCNR deposit eligibility and tax exemptions.
13. `loan_application_process`: 5-stage lifecycle from submission through disbursement.

### 3. Chunking Strategies & Vector Indexing (`credobot/rag/`)
Two chunking strategies indexed in separate ChromaDB collections (`collection.upsert()`):
- **Fixed-Size with Overlap (`kb_fixed`):** Character window size 200, overlap 50, forward whitespace snap 20 chars. Total: **62 chunks**.
- **Sentence-Based Chunking (`kb_sentence`):** Consecutive 2-sentence groups. Total: **26 chunks**.
*See [`transcripts/part1_index.md`](transcripts/part1_index.md).*

### 4. IDK Threshold Calibration
Top-1 cosine similarity measured across 6 in-scope and 3 out-of-scope queries:
| Collection | Min In-Scope Sim | Max Out-of-Scope Sim | Gap | Chosen Threshold |
|---|---|---|---|---|
| `kb_fixed` | 0.4132 | 0.1894 | +0.2238 | **0.29** |
| `kb_sentence` | 0.3889 | 0.0770 | +0.3119 | **0.29** |
| **Overall** | **0.3889** | **0.1894** | **+0.1995** | **0.29** |

*Threshold Selection:* `IDK_THRESHOLD = 0.29` set at the exact midpoint separating lowest in-scope similarity (0.3889) and highest out-of-scope similarity (0.1894).
*See [`transcripts/part1_calibration.md`](transcripts/part1_calibration.md) and [`transcripts/part1_grounded.md`](transcripts/part1_grounded.md).*

### 5. Chunking Evaluation (Precision & Recall)
Evaluated across 5 representative policy queries:
- **`kb_fixed`:** Precision = **0.8333**, Recall = **1.0000**, Macro F1 = **0.9091**
- **`kb_sentence`:** Precision = **0.5833**, Recall = **1.0000**, Macro F1 = **0.7368**

**Deployment Recommendation:**
> "We recommend deploying `kb_fixed` for production retrieval. In our empirical evaluation across in-scope policy queries, `kb_fixed` achieved a superior macro-averaged Precision of 0.8333, Recall of 1.0000, and F1 score of 0.9091, compared to `kb_sentence` which achieved Precision of 0.5833, Recall of 1.0000, and F1 score of 0.7368. Fixed-size chunking with character overlap consistently concentrates top-k retrieved chunks within the exact target policy documents, eliminating cross-document noise while preserving 100% recall."

*See [`transcripts/part1_chunking_eval.md`](transcripts/part1_chunking_eval.md).*

---

## Part 2 — CrewAI Multi-Agent Orchestration with Tools, Memory & Guardrails

### 6. Loan Status Lookup & Escalation Formula (`credobot/tools/loan_status.py`)
`check_loan_application_status(record_id: str) -> dict` evaluates:

$$\text{EscalationScore} = 0.55 \times \text{FraudFlag} + 0.45 \times \left( \frac{\text{DaysSinceCreated}}{30} \times \text{StatusWeight} \right)$$

where:
- `escalation_score = 0.55 * flagged_for_fraud_review + 0.45 * (days_since_created / 30 * status_weight)`
- `status_weight = 0.5` if status $\in$ `{"Rejected", "Disbursed"}` else `1.0`.

- **Escalation Threshold:** `0.55`.
- **Distribution Justification:** The 80th percentile of application age in our dataset is 25.0 days. Under this formula, even an application at the 30-day maximum without a fraud flag reaches at most $0.45 \times 1.0 = 0.450 < 0.55$. Therefore, reaching $\ge 0.55$ strictly requires `flagged_for_fraud_review=True`. In our dataset, exactly **12 / 60 records (20.0%)** escalate.
*See [`transcripts/part2_escalation.md`](transcripts/part2_escalation.md).*

### 7. CrewAI Multi-Agent Crew (`credobot/crew/crew.py`)
Constructed with 3 sequential agents:
1. `RetrievalAgent`: Equipped exclusively with `rag_lookup_tool`.
2. `LookupAgent`: Equipped exclusively with `loan_status_lookup_tool`.
3. `ResponseComposerAgent`: Synthesizes tool outputs into the structured response.
*See [`transcripts/part2_crew.md`](transcripts/part2_crew.md).*

### 8. Session Memory (`credobot/memory.py`)
Multi-turn session memory powered by LangChain's `RunnableWithMessageHistory`:
- Resolves pronoun references across turns (e.g., Turn 1: "What is the status of LA-1007?", Turn 2: "Is it approved?").
- Fresh session IDs isolate state completely without bleed.
*See [`transcripts/part2_memory_multiturn.md`](transcripts/part2_memory_multiturn.md) and [`transcripts/part2_memory_fresh.md`](transcripts/part2_memory_fresh.md).*

### 9. Structured Output Schema (`credobot/crew/schemas.py`)
Every crew response validates against `CrewResponse`:
```python
class CrewResponse(BaseModel):
    intent: Literal["policy", "status", "unknown"]
    answer: str
    grounded: bool
    escalate: bool
    sources: list[str]
```

### 10. Guardrails (`credobot/guardrails/`)
- **Input PII Masking:** Regex redaction replacing fixed-format Indian PII (`[PAN_MASKED]`, `[AADHAAR_MASKED]`, `[ACCOUNT_MASKED]`).
- **Input Prompt Injection:** Detects adversarial patterns (system prompt leakage, instruction overrides) and returns standard refusal.
- **Output Groundedness:** Verifies sentence entailment against retrieved context (`SUPPORT_THRESHOLD = 0.81`).
*See [`transcripts/part2_guardrails.md`](transcripts/part2_guardrails.md).*

---

## Part 3 — Evaluation, Observability & FastAPI Deployment

### 11. FastAPI Deployment (`credobot/api/app.py`)
- `POST /ask`: Request/Response with Pydantic validation (`AskRequest` / `AskResponse`).
- `POST /add-document`: Upserts new knowledge-base policy markdown documents into ChromaDB.
- `GET /health`: System telemetry, cache statistics, and uptime check.
- `WebSocket /ws/chat`: Real-time streaming chat handling client disconnects (`WebSocketDisconnect`) gracefully without crashing the server.
*See [`transcripts/part3_api.md`](transcripts/part3_api.md).*

### 12. Structured JSONL Logging (`credobot/api/logging_mw.py`)
Every HTTP and WebSocket interaction logs a single JSONL audit entry with:
- `trace_id`: Unique UUID4 per transaction.
- `duration_ms`: Wall-clock execution time.
- `query_masked`: Masked input query ensuring raw PII never touches disk.
*Sample log entry:*
```json
{"timestamp": "2026-11-08T15:27:00.123456+00:00", "trace_id": "f8a7b6c5-d4e3-4210-9876-543210abcdef", "endpoint": "/ask", "method": "POST", "status_code": 200, "duration_ms": 14.2, "session_id": "sess-default", "query_masked": "My PAN is [PAN_MASKED], check LA-1007", "intent": "status", "grounded": true, "escalate": false, "error": null}
```

### 13. LLM-as-Judge Evaluation (15 Queries)
A 15-case test set covering all 12 required KB topics plus 3 edge/OOS cases evaluated by a deterministic judge:
- **Macro Accuracy:** `0.7660`
- **Macro Grounding:** `1.0000`
- **Macro Completeness:** `0.6007`
- **Macro Safety:** `1.0000`
- Total Evaluated Queries: 15 / 15
*See [`transcripts/part3_eval.md`](transcripts/part3_eval.md) and [`transcripts/part3_eval.jsonl`](transcripts/part3_eval.jsonl).*

---

## Part 4 — Resilience & Governance

### 14. AutoGen Review Stage (`credobot/review/autogen_review.py`)
A 2-agent `RoundRobinGroupChat` (`max_turns=2`):
- `PolicyComplianceReviewer`: Verifies policy claims against retrieved context.
- `FinalEditor`: Produces validated `ReviewVerdict(approved=..., final_answer=..., reason=...)`.
- Demonstrates approving compliant answers and modifying ungrounded claims.
*See [`transcripts/part4_review.md`](transcripts/part4_review.md).*

### 15. AI Governance Framework (`credobot/governance/`)
- **Application Layer (Least Autonomy ACL):**
  Only `LookupAgent` has permission to call `check_loan_application_status`. Wiring the tool to `RetrievalAgent` or `ResponseComposer` raises `GovernanceViolationError`.
- **System Risk Classification:**
  **Classified as HIGH RISK.**
  *Justification:* CredoBot accesses non-public customer banking records, inspects underwriting decisions, processes fixed-format PII (PAN, Aadhaar), and outputs financial policy interpretations affecting consumer rights and liabilities under RBI regulatory guidelines.
- **Runtime Budget & Cost Guard:**
  Limits per-request token usage to `6,000` tokens and cost to `$0.01` (nominal `$0.0006` / 1k tokens). Oversized requests trigger `BudgetExceededError`.
*See [`transcripts/part4_governance.md`](transcripts/part4_governance.md).*

### 16. Response Cache (`credobot/cache.py`)
Thread-safe LRU response cache with Unicode NFKC normalization and punctuation stripping:
- Avoids redundant RAG and LLM tool calls on repeated inquiries.
- Verified in `transcripts/part4_cache.md` with counter evidence (`cache.miss` = 1, `cache.hit` = 1).
*See [`transcripts/part4_cache.md`](transcripts/part4_cache.md).*

---

## Complete Graded Transcripts Index
Every graded deliverable is linked in [`transcripts/INDEX.md`](transcripts/INDEX.md):
- [Dataset Design (`part1_dataset.md`)](transcripts/part1_dataset.md)
- [Dual Indexing (`part1_index.md`)](transcripts/part1_index.md)
- [Threshold Calibration (`part1_calibration.md`)](transcripts/part1_calibration.md)
- [Grounded Generation (`part1_grounded.md`)](transcripts/part1_grounded.md)
- [Chunking Comparison (`part1_chunking_eval.md`)](transcripts/part1_chunking_eval.md)
- [Escalation Scoring (`part2_escalation.md`)](transcripts/part2_escalation.md)
- [CrewAI Crew (`part2_crew.md`)](transcripts/part2_crew.md)
- [Multi-Turn Memory (`part2_memory_multiturn.md`)](transcripts/part2_memory_multiturn.md)
- [Fresh Session Isolation (`part2_memory_fresh.md`)](transcripts/part2_memory_fresh.md)
- [Guardrails (`part2_guardrails.md`)](transcripts/part2_guardrails.md)
- [FastAPI & Logging (`part3_api.md`)](transcripts/part3_api.md)
- [LLM-as-Judge Evaluation (`part3_eval.md`)](transcripts/part3_eval.md)
- [AutoGen Review Stage (`part4_review.md`)](transcripts/part4_review.md)
- [AI Governance & Budget (`part4_governance.md`)](transcripts/part4_governance.md)
- [Response Caching (`part4_cache.md`)](transcripts/part4_cache.md)
- [End-to-End Pipeline (`pipeline_e2e.md`)](transcripts/pipeline_e2e.md)

---

## Testing & Verification

Run the entire automated test suite:
```bash
uv run pytest -q
```
*Current test suite: 143+ passing tests across 20 test modules covering data generation, vector indexing, retrieval, guardrails, memory, crew orchestration, review, FastAPI, and repository completeness.*

---

## Project Documentation & Architecture
- [System Architecture & Mermaid Flows (`architecture.md`)](architecture.md)
- [New Member Onboarding & Contribution Guide (`CONTRIBUTING.md`)](CONTRIBUTING.md)
- [Technical Synthesis & Executive Report (`docs/REPORT.md`)](docs/REPORT.md)
- [Empirical Parameters & Measured Decisions (`docs/DECISIONS.md`)](docs/DECISIONS.md)
- [Environment Setup Guide (`docs/SETUP.md`)](docs/SETUP.md)
- [Project Requirements Brief (`docs/BRIEF.md`)](docs/BRIEF.md)

