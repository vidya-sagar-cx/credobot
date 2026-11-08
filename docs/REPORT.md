# CredoBot Technical Report & Architectural Synthesis

**Track:** Finance (Banking & FinTech)  
**System:** CredoBot Loan-Support Agent  
**Environment:** Zero-Network, Fully Deterministic (`MOCK_LLM=true`)  
**Repository Branch:** `feat/loan-support-agent`

---

## 1. Executive Summary

Modern banking support systems require reconciling natural language accessibility with rigorous regulatory compliance, deterministic policy enforcement, and confidential data privacy. CredoBot was designed for CRED's lending operations team to resolve retail customer inquiries across 12 distinct policy categories and inspect active loan application records while guaranteeing strict alignment with statutory banking guidelines (e.g., RBI fair lending and digital lending directives).

The system integrates:
1. Local dense vector retrieval over an authored retail banking knowledge base.
2. Sequential 3-agent orchestration via CrewAI for distinct role-based tasks.
3. Multi-turn LangChain conversation memory with antecedent entity resolution.
4. Input and output guardrails mitigating prompt injection, ungrounded fabrication, and fixed-format PII leakage.
5. An independent 2-agent AutoGen review team validating factual correctness before response emission.
6. A four-layer AI governance framework enforcing least-autonomy tool ACLs and per-request runtime budget caps.
7. A FastAPI production deployment with graceful WebSocket disconnect handling and ELK-compatible JSON-Lines structured audit logging.

All components run deterministically with zero API keys and zero outbound network calls (`network calls attempted: 0`).

---

## 2. End-to-End Pipeline Architecture

The runtime architecture processes queries through 7 strictly sequenced gates:

```
                  +----------------------------------+
                  |         Incoming Query           |
                  +-----------------+----------------+
                                    |
                                    v
                  +----------------------------------+
                  | Stage 1: Governance & Budget     |
                  | - Rate/Cost ceiling verification |
                  | - Tool ACL least-autonomy gate   |
                  +-----------------+----------------+
                                    |
                                    v
                  +----------------------------------+
                  | Stage 2: Input Guardrails        |
                  | - Fixed PII Redaction (PAN/UID)  |
                  | - Adversarial injection filter   |
                  +-----------------+----------------+
                                    |
                                    v
                  +----------------------------------+
                  | Stage 3: Session Memory & Cache  |
                  | - Multi-turn entity rewriting    |
                  | - LRU query cache lookup (NFKC)  |
                  +-----------------+----------------+
                                    |
                                    v
                  +----------------------------------+
                  | Stage 4: CrewAI Multi-Agent Crew |
                  | - RetrievalAgent (RAG tool)      |
                  | - LookupAgent (Status tool)      |
                  | - ResponseComposerAgent          |
                  | - CrewResponse Schema Validation |
                  +-----------------+----------------+
                                    |
                                    v
                  +----------------------------------+
                  | Stage 5: Output Guardrail        |
                  | - Groundedness Entailment Check  |
                  |   (SUPPORT_THRESHOLD = 0.81)     |
                  +-----------------+----------------+
                                    |
                                    v
                  +----------------------------------+
                  | Stage 6: AutoGen Review Stage    |
                  | - RoundRobinGroupChat (2 agents) |
                  | - ReviewVerdict Pydantic Schema  |
                  +-----------------+----------------+
                                    |
                                    v
                  +----------------------------------+
                  | Stage 7: Delivery & Audit Log    |
                  | - JSONL trace emission (no PII)  |
                  | - Masked response returned       |
                  +----------------------------------+
```

---

## 3. Empirical Design & Calibration Results

### 3.1 Synthetic Loan Dataset (`dataset.py`)
- **Parameters:** Seed = 2026, Sample Size $N = 60$.
- **Distribution:** Personal Loan (22), Auto Loan (12), Home Loan (11), Business Loan (9), Education Loan (6).
- **Status Breakdown:** Under Review (22), Approved (15), Disbursed (10), Rejected (7), Submitted (6).
- **Fraud Rate:** Exactly 12 / 60 records (20.0%) were flagged for fraud review, satisfying the required 10%–30% threshold on the initial seeded draw.
- **Credit Limits:** Tiered dynamically between ₹50,000 (unsecured micro-personal) up to ₹20,000,000 (secured MSME business lines).

### 3.2 Dual Chunking & Vector Retrieval Evaluation (`kb_fixed` vs `kb_sentence`)
Thirteen authoritative policy documents were chunked using two separate strategies and indexed in ChromaDB collections using `sentence-transformers/all-MiniLM-L6-v2`:
1. **Fixed-Size with Overlap (`kb_fixed`):** Window = 200 chars, Overlap = 50 chars, Snap = 20 chars. Produced 62 chunks.
2. **Sentence-Based (`kb_sentence`):** 2 sentences per chunk. Produced 26 chunks.

**Empirical Comparison:**
| Chunking Strategy | Indexed Chunks | Precision | Recall | Macro F1 |
|---|---|---|---|---|
| `kb_fixed` | 62 | **0.8333** | **1.0000** | **0.9091** |
| `kb_sentence` | 26 | 0.5833 | 1.0000 | 0.7368 |

**Finding:** Fixed-size chunking with character overlap was selected for production deployment (`config.DEPLOY_COLLECTION = "kb_fixed"`). Fixed chunking concentrates top-$k$ vectors within the exact target document, achieving superior Precision (+0.2500) and F1 (+0.1723) without sacrificing Recall.

### 3.3 "I Don't Know" Fallback Calibration
To eliminate hallucination on out-of-scope (OOS) inputs without relying on an external judge API, cosine similarity distributions were calibrated across 6 in-scope and 3 out-of-scope queries:
- Minimum In-Scope Cosine Similarity: `0.3889`
- Maximum Out-of-Scope Cosine Similarity: `0.1894`
- Calibrated Fallback Boundary: `IDK_THRESHOLD = 0.29` (exact midpoint separating distributions by a margin of $\pm 0.0995$).

### 3.4 Loan Status Escalation Formula
The escalation function balances fraud urgency with operational aging:

$$\text{EscalationScore} = 0.55 \times \text{FraudFlag} + 0.45 \times \left( \frac{\text{DaysSinceCreated}}{30} \times \text{StatusWeight} \right)$$

where:
- `escalation_score = 0.55 * flagged_for_fraud_review + 0.45 * (days_since_created / 30 * status_weight)`
- `status_weight = 0.5` for terminal states (`Rejected`, `Disbursed`) and `1.0` for active states.
- **Threshold Selection:** `0.55`.
- **Operational Justification:** Applications older than the 80th percentile (25.0 days) reach at most $0.45 \times (30/30) = 0.450 < 0.55$. Hence, an active fraud alert is mathematically required to trigger human escalation, resulting in exactly 12 / 60 escalations (20.0%).

---

## 4. Multi-Agent Orchestration & Governance

### 4.1 CrewAI Implementation Details & Pitfalls Mitigated
CrewAI's native orchestration relies on `crewai.llms.base_llm.BaseLLM`. In offline mock environments, two critical architectural pitfalls were addressed:
1. **ReAct Prompt Reflection Avoidance:** Built-in CrewAI system templates embed the literal text `"Observation: the result of the action"`. A naive parser extracts template text prematurely; CredoBot isolates generated completions from static prompt templates.
2. **Schema-Based Tool Dispatch:** Arguments are resolved against declared Pydantic schemas rather than string matching tool names, avoiding false dispatch collisions (e.g., confusing `rag_lookup` with status lookup).

### 4.2 AutoGen GroupChat Review Stage
Draft answers synthesized by CrewAI's `ResponseComposerAgent` are routed to an AutoGen 2-agent `RoundRobinGroupChat` (`PolicyComplianceReviewer` + `FinalEditor`, `max_turns=2`). The stage outputs a validated `ReviewVerdict`:
- Compliant drafts are approved unchanged.
- Factually unsupported or hallucinated policy commitments are detected and corrected before publication.

### 4.3 AI Governance Controls
- **Application Layer:** Enforces the principle of least autonomy. Only `LookupAgent` holds tool permissions for `check_loan_application_status`. Any invocation attempt by other agents raises a `GovernanceViolationError`.
- **Risk Classification:** Classified as **HIGH RISK** under the enterprise risk framework due to processing sensitive financial applicant records, assessing creditworthiness decisions, and outputting legally binding banking terms.
- **Runtime Budget Layer:** Enforces a per-transaction limit of 6,000 tokens and $0.01 cost ceiling, aborting oversized adversarial inputs.

---

## 5. Quantitative LLM-as-Judge Evaluation

A 15-case test suite was evaluated across all 12 mandatory policy categories, out-of-scope questions, prompt injections, and PII edge cases using an automated judge:

| Dimension | Macro Average Score | Benchmark Standard |
|---|---|---|
| **Accuracy** | **0.7660** | Factual correctness against reference key points |
| **Grounding** | **1.0000** | Strict entailment against retrieved context |
| **Completeness** | **0.6007** | Coverage of reference document clauses |
| **Safety** | **1.0000** | Zero PII leaks, zero injection compromises |


*Evaluation Notes:* Grounding achieved 1.0000 because ungrounded assertions are refused or revised upstream by the stage-5 output guardrail (`SUPPORT_THRESHOLD = 0.81`) and the AutoGen review team. Safety achieved 1.0000 due to reliable regex sanitization of all fixed-format Indian identifiers (PAN, Aadhaar, Account numbers).

---

## 6. Observability & Deployment Verification

1. **FastAPI & WebSockets:** Implements `POST /ask`, `POST /add-document`, and `GET /health`. The WebSocket endpoint `/ws/chat` gracefully catches `WebSocketDisconnect` events without thread pool starvation.
2. **Structured JSON-Lines Logging:** Emits ELK-formatted logs with monotonic timing and masked PII.
3. **Response Caching:** Normalizes Unicode NFKC representations and punctuation, demonstrating zero-overhead cache hits on identical requests.
4. **Offline Suite Runner:** `credobot.demos.run_all` sequentially executes all 15 component demonstrations, validating network isolation (`network calls attempted: 0`) and generating self-contained Markdown transcripts in `transcripts/`.

---

## 7. Conclusion

CredoBot demonstrates that multi-agent systems in high-risk financial domains can achieve robust safety, deterministic guardrails, and rigorous compliance without dependency on proprietary cloud APIs. The entire repository is reproducible from a single command, fully covered by 150 automated tests, and audited against statutory FinTech standards.
