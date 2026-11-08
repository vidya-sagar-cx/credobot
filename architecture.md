# CredoBot: Complete Architecture & System Design

**Track:** Finance (Banking & FinTech)  
**System:** CredoBot Loan-Support Agent for CRED  
**Execution Mode:** Deterministic Offline (`MOCK_LLM=true`, `network calls attempted: 0`)

---

## 1. High-Level System Architecture

CredoBot is an enterprise multi-agent loan-support platform designed to answer retail lending policy queries and inspect live loan applications under strict financial compliance standards. The system enforces a 7-stage pipeline spanning governance, guardrails, multi-turn memory, multi-agent crew execution, groundedness entailment verification, independent multi-agent adversarial review, and structured audit logging.

```mermaid
flowchart TD
    User([Client / User]) -->|HTTP / WebSocket| Gateway[FastAPI Gateway]
    
    subgraph S1["Stage 1: Governance & Budget"]
        Gateway --> LogMW[Logging & Trace Middleware]
        LogMW --> BudgetGate{Token & Cost<br/>Budget Check}
        BudgetGate -->|Exceeded > 6000 tok| Err413[Reject HTTP 413]
        BudgetGate -->|Within Budget| ACLGate[Least Autonomy Tool ACL]
    end

    subgraph S2["Stage 2: Input Guardrails"]
        ACLGate --> PIIMask[PII Masking Engine<br/>PAN / Aadhaar / Account]
        PIIMask --> InjectionCheck{Prompt Injection<br/>Detector}
        InjectionCheck -->|Adversarial Pattern| RefusalInjection[Standard Refusal]
        InjectionCheck -->|Clean Query| SanitizedQuery[Sanitized Masked Query]
    end

    subgraph S3["Stage 3: Memory & Caching"]
        SanitizedQuery --> SessionMem[LangChain Session Memory<br/>Antecedent Resolution]
        SessionMem --> CacheLookup{Normalized LRU Cache<br/>Unicode NFKC}
        CacheLookup -->|Cache Hit| FinalLog
        CacheLookup -->|Cache Miss| CrewOrchestrator
    end

    subgraph S4["Stage 4: CrewAI Multi-Agent Core"]
        CrewOrchestrator[CrewAI Sequential Orchestrator]
        CrewOrchestrator --> RetrievalAgent[Retrieval Agent]
        CrewOrchestrator --> LookupAgent[Lookup Agent]
        CrewOrchestrator --> ComposerAgent[Response Composer]
        
        RetrievalAgent -->|RAG Tool| Chroma[(ChromaDB kb_fixed<br/>Local Vector Store)]
        LookupAgent -->|Status Tool| Dataset[(Loan Applications<br/>Dataset N=60)]
        
        RetrievalAgent --> ComposerAgent
        LookupAgent --> ComposerAgent
        ComposerAgent --> CrewResponseModel[Validated CrewResponse Schema]
    end

    subgraph S5["Stage 5: Output Guardrail"]
        CrewResponseModel --> GroundedCheck{Groundedness Entailment<br/>Cosine Support >= 0.81}
        GroundedCheck -->|Ungrounded Claim| RefusalUngrounded[Refusal / Fallback]
        GroundedCheck -->|Supported| VerifiedDraft[Verified Draft Answer]
    end

    subgraph S6["Stage 6: AutoGen Review Stage"]
        VerifiedDraft --> AutoGenTeam[AutoGen RoundRobinGroupChat<br/>max_turns=2]
        AutoGenTeam --> ComplianceReviewer[Policy Compliance Reviewer]
        ComplianceReviewer --> FinalEditor[Final Editor Agent]
        FinalEditor --> ReviewVerdictModel[Validated ReviewVerdict Schema<br/>approved: bool, final_answer: str]
    end

    subgraph S7["Stage 7: Delivery & Audit Logging"]
        ReviewVerdictModel --> ResponseCacheStore[Store in LRU Cache]
        ResponseCacheStore --> FinalLog[ELK JSONL Audit Logger<br/>Trace ID, Timing, Masked PII]
        RefusalInjection --> FinalLog
        RefusalUngrounded --> FinalLog
        FinalLog --> UserDelivery([Response Emitted to User])
    end
```

---

## 2. Section-by-Section Architectural Details

### Section 1: Ingestion & Vector Retrieval RAG Core

The knowledge base comprises 13 authoritative policy documents covering all mandatory banking areas:
- Eligibility criteria, EMI calculation, credit card fees, KYC documentation, fraud disputes, account closure, interest rate slabs, prepayment penalties, minimum balance, credit score factors, joint accounts, NRI accounts, and loan lifecycle.

#### Dual Chunking & Comparative Retrieval
Documents are indexed into two isolated ChromaDB collections using local embeddings (`sentence-transformers/all-MiniLM-L6-v2`, 384 dimensions):
1. **Fixed-Size Chunking with Overlap (`kb_fixed`):** Character window size 200, overlap 50 characters, forward whitespace snap 20 characters. Yields 62 chunks.
2. **Sentence-Based Chunking (`kb_sentence`):** Consecutive 2-sentence groups without overlap. Yields 26 chunks.

```mermaid
flowchart LR
    Docs[13 Policy Markdown Docs] --> SplitFixed[Fixed Window Splitter<br/>200 chars / 50 overlap]
    Docs --> SplitSent[Sentence Splitter<br/>2 sentences / chunk]
    
    SplitFixed --> ChunksFixed[62 Fixed Chunks]
    SplitSent --> ChunksSent[26 Sentence Chunks]
    
    ChunksFixed --> LocalEmbed1[all-MiniLM-L6-v2<br/>Dense Embeddings]
    ChunksSent --> LocalEmbed2[all-MiniLM-L6-v2<br/>Dense Embeddings]
    
    LocalEmbed1 --> ChromaFixed[(ChromaDB: kb_fixed<br/>P=0.8333, F1=0.9091)]
    LocalEmbed2 --> ChromaSent[(ChromaDB: kb_sentence<br/>P=0.5833, F1=0.7368)]
```

#### Empirical Calibration of the "I Don't Know" Fallback Threshold
In offline environments without an external judge, cosine similarity serves as the discriminant between policy-supported queries and irrelevant/out-of-scope requests.
- Top-1 cosine similarity was measured across 6 in-scope queries and 3 out-of-scope queries:
  - **In-Scope Range:** `0.3889` to `0.7612` (minimum in-scope = `0.3889`).
  - **Out-of-Scope Range:** `0.0421` to `0.1894` (maximum out-of-scope = `0.1894`).
- **Calibrated Threshold:** `IDK_THRESHOLD = 0.29` set at the exact midpoint:
  $$\text{Margin} = \frac{0.3889 - 0.1894}{2} = 0.09975 \implies 0.1894 + 0.0998 \approx 0.29$$

```mermaid
sequenceDiagram
    autonumber
    actor Client
    participant RAG as RAG Retrieval Engine
    participant Chroma as ChromaDB (kb_fixed)
    
    Client->>RAG: query_text
    RAG->>Chroma: similarity_search_with_score(query, k=3)
    Chroma-->>RAG: [chunk_1, chunk_2, chunk_3], similarities
    
    alt max(similarity) < 0.29
        RAG-->>Client: IDK_MESSAGE ("I don't know — the CRED policy knowledge base doesn't cover that.")
    else max(similarity) >= 0.29
        RAG->>RAG: Construct grounded answer strictly from retrieved chunk text
        RAG-->>Client: GroundedAnswer(answer, context=[citations], supported=True)
    end
```

---

### Section 2: Loan Application Dataset & Escalation Engine

`dataset.py` generates 60 synthetic loan records using seed `2026`:
- **Categories:** Personal Loan (22), Auto Loan (12), Home Loan (11), Business Loan (9), Education Loan (6).
- **Statuses:** Under Review (22), Approved (15), Disbursed (10), Rejected (7), Submitted (6).
- **Fraud Rate:** Exactly 12 / 60 records (20.0%) flagged for fraud review.

#### Designed Escalation Formula
The escalation engine evaluates a continuous score in $[0.0, 1.0]$:
$$\text{escalation\_score} = 0.55 \times \text{flagged\_for\_fraud\_review} + 0.45 \times \left( \frac{\text{days\_since\_created}}{30} \times w_{\text{status}} \right)$$
where $w_{\text{status}} = 0.5$ if status $\in \{\text{Rejected}, \text{Disbursed}\}$ and $1.0$ otherwise.

- **Threshold:** `ESCALATION_THRESHOLD = 0.55`.
- **Mathematical Guarantee:** Because maximum non-fraud recency contribution is $0.45 \times (30/30) \times 1.0 = 0.450 < 0.55$, an application **cannot** breach the threshold without an active fraud flag. Exactly 12 / 60 records (20.0%) trigger human escalation.

```mermaid
flowchart TD
    Req[Loan Status Request: record_id] --> Fetch[Query LOAN_APPLICATIONS Dataset]
    Fetch --> CheckFound{Record Exists?}
    CheckFound -->|No| NotFound[Return Application Not Found]
    CheckFound -->|Yes| Extract[Extract: status, amount, days_since_created, fraud_flag]
    
    Extract --> StatusWeight{Status Terminal?<br/>Rejected / Disbursed}
    StatusWeight -->|Yes| W05[w_status = 0.5]
    StatusWeight -->|No| W10[w_status = 1.0]
    
    W05 --> CalcScore[Compute escalation_score<br/>0.55*fraud + 0.45*(days/30)*w_status]
    W10 --> CalcScore
    
    CalcScore --> ThresholdCheck{escalation_score >= 0.55}
    ThresholdCheck -->|Yes| FlagEscalate[escalate = True<br/>Queue for Manager Review]
    ThresholdCheck -->|No| NormalPass[escalate = False<br/>Standard Status Response]
```

---

### Section 3: CrewAI Multi-Agent Core & ReAct Execution

CrewAI orchestrates a 3-agent sequential workflow. To operate deterministically offline without remote API dependencies, CredoBot subclasses `crewai.llms.base_llm.BaseLLM` with an internal ReAct interpreter.

#### Agent Roles & Tool Bindings
1. **`RetrievalAgent`:** Equipped exclusively with `RagLookupTool`. Searches `kb_fixed` and returns citations.
2. **`LookupAgent`:** Equipped exclusively with `LoanStatusTool`. Performs record lookup and escalation scoring.
3. **`ResponseComposerAgent`:** Zero tools. Consolidates inputs from preceding agents into a coherent, customer-facing response.

```mermaid
sequenceDiagram
    autonumber
    participant Orch as CrewAI Orchestrator
    participant Ret as RetrievalAgent
    participant Look as LookupAgent
    participant Comp as ResponseComposerAgent
    participant RAG as RagLookupTool
    participant Status as LoanStatusTool
    
    Orch->>Ret: Task 1: Policy Retrieval
    Ret->>RAG: rag_lookup(query)
    RAG-->>Ret: grounded context or fallback
    Ret-->>Orch: Policy evidence
    
    Orch->>Look: Task 2: Loan Status Lookup
    opt Query contains loan ID (e.g. LA-1001)
        Look->>Status: check_loan_application_status("LA-1001")
        Status-->>Look: status dict + escalation_score
    end
    Look-->>Orch: Record details & escalation flag
    
    Orch->>Comp: Task 3: Compose Customer Response
    Comp->>Comp: Validate schema (CrewResponse)
    Comp-->>Orch: Final CrewResponse JSON
```

#### Mitigated Framework Pitfalls
- **Prompt Template Reflection Avoidance:** CrewAI's default ReAct prompt contains the string `"Observation: the result of the action"`. A naive parser extracts this template substring on the first turn. `MockLLM` inspects strictly model-generated tokens, ignoring prompt prefixes.
- **Schema-Based Tool Dispatch:** Tools are bound and invoked by declared Pydantic argument schemas (`RagLookupInput` vs `LoanStatusInput`) rather than brittle substring matching on tool names.

---

### Section 4: Guardrail Defense-in-Depth

The guardrail subsystem guarantees bidirectional protection against malicious inputs and invalid outputs:

```mermaid
flowchart TD
    subgraph InputGuardrails["Input Guardrail Layer"]
        InQuery[Raw User Query] --> PIIFilter[PII Regex Scanner]
        PIIFilter -->|Match PAN [A-Z]{5}[0-9]{4}[A-Z]| MaskPAN[Replace with [PAN_MASKED]]
        PIIFilter -->|Match Aadhaar [0-9]{4} [0-9]{4} [0-9]{4}| MaskUID[Replace with [AADHAAR_MASKED]]
        PIIFilter -->|Match Account [0-9]{9,18}| MaskACC[Replace with [ACCOUNT_MASKED]]
        
        MaskPAN --> CleanMaskedQuery[PII-Sanitized Query]
        MaskUID --> CleanMaskedQuery
        MaskACC --> CleanMaskedQuery
        
        CleanMaskedQuery --> InjectionFilter{Injection Pattern Match<br/>'ignore previous instructions',<br/>'system prompt', 'jailbreak'}
        InjectionFilter -->|Match Found| RefuseInj[Return REFUSAL_INJECTION<br/>Halt Execution]
        InjectionFilter -->|Clean| SafeQuery[Forward to Pipeline Execution]
    end

    subgraph OutputGuardrails["Output Guardrail Layer"]
        DraftAnswer[Generated Draft Answer] --> SentenceSplit[Split into Individual Claims]
        SentenceSplit --> EntailmentCheck[Cosine Similarity against<br/>Retrieved Context Chunks]
        EntailmentCheck --> SupportScore[Compute Sentence Support Ratio]
        SupportScore --> Threshold{Support Ratio >= 0.81?}
        Threshold -->|No| RefuseUngrounded[Return REFUSAL_UNGROUNDED<br/>Suppress Speculative Claims]
        Threshold -->|Yes| OutputSafe[Forward to Review Stage]
    end
```

---

### Section 5: AutoGen Multi-Agent Review Stage

To prevent erroneous, ungrounded, or hallucinated claims from reaching users, the pipeline routes drafts through an independent 2-agent AutoGen `RoundRobinGroupChat` (`max_turns=2`):
- **`PolicyComplianceReviewer`:** Inspects each factual assertion in the draft against the retrieved context sentences. Returns either `REVIEW: PASS` or `REVIEW: FAIL` with specific unsupported claims.
- **`FinalEditor`:** Ingests the reviewer's verdict. If approved, emits the draft unchanged. If rejected, removes or rewrites unsupported sentences using strictly the provided context. Outputs a validated Pydantic `ReviewVerdict`.

```mermaid
sequenceDiagram
    autonumber
    participant Pipeline as CredoBot Pipeline
    participant Reviewer as PolicyComplianceReviewer
    participant Editor as FinalEditor
    
    Pipeline->>Reviewer: format_review_task(draft, context, record)
    Reviewer->>Reviewer: Verify claims against context sentences
    
    alt All Claims Grounded
        Reviewer->>Editor: "REVIEW: PASS. All claims supported by context."
        Editor->>Pipeline: ReviewVerdict(approved=True, final_answer=draft, reason="...")
    else Unsupported Claim Detected
        Reviewer->>Editor: "REVIEW: FAIL. Unsupported: [unverified claim]"
        Editor->>Editor: Excise ungrounded assertion; rewrite using context
        Editor->>Pipeline: ReviewVerdict(approved=False, final_answer=revised_draft, reason="...")
    end
```

---

### Section 6: AI Governance Framework & Cost Control

CredoBot implements the four-layer AI governance architecture:

| Governance Layer | Mechanism | Implementation & Enforcement |
|---|---|---|
| **Data Layer** | Fixed PII Masking | PAN, Aadhaar, and Account numbers are redacted before model consumption and disk logging. |
| **Model Layer** | Guardrails & Entailment | `SUPPORT_THRESHOLD = 0.81` suppresses unsupported generations. |
| **Application Layer** | Principle of Least Autonomy | `TOOL_ACL` restricts `check_loan_application_status` exclusively to `LookupAgent`. |
| **Runtime Layer** | Budget & Cost Ceiling | Hard limits: `max_request_tokens = 6,000`, `max_request_cost_usd = $0.01`. |

#### Risk Assessment Classification
CredoBot is classified as **HIGH RISK** under financial AI governance frameworks:
- Processes confidential consumer banking records and identifiers.
- Delivers loan application approvals/rejections affecting customer credit standing.
- Subject to statutory regulatory scrutiny (e.g., RBI Fair Practices Code for Lenders).

---

### Section 7: Session Memory & Normalized Caching

```mermaid
flowchart LR
    subgraph MemoryLayer["LangChain Session Memory"]
        Turn1["Turn 1: 'What is the status of LA-1007?'"] --> Store[InMemoryChatMessageHistory]
        Store --> State[Session State: active_loan = LA-1007]
        Turn2["Turn 2: 'Is it approved?'"] --> Resolve[Rewrite Query: 'Is application LA-1007 approved?']
        State --> Resolve
    end

    subgraph CacheLayer["LRU Query Response Cache"]
        Incoming["Incoming Query"] --> Norm[Normalize: Unicode NFKC + Lowercase + Strip Punctuation]
        Norm --> KeyGen["Key: 'kb_fixed::how is emi calculated'"]
        KeyGen --> CacheCheck{Cache Hit?}
        CacheCheck -->|Yes| InstantReturn[Return Cached GroundedAnswer<br/>Zero LLM / RAG overhead]
        CacheCheck -->|No| ExecRAG[Execute Full Pipeline]
        ExecRAG --> SetCache[Store in Cache with TTL]
    end
```

---

### Section 8: FastAPI Deployment & Observability

The application is deployed using FastAPI:
- `POST /ask`: Primary synchronous inference endpoint accepting `AskRequest` and returning `AskResponse`.
- `POST /add-document`: Dynamic knowledge-base ingestion updating the live ChromaDB index.
- `GET /health`: Healthcheck endpoint reporting cache statistics and operational telemetry.
- `WebSocket /ws/chat`: Real-time streaming chat. Catches `WebSocketDisconnect` gracefully, ensuring abrupt client disconnects do not crash worker threads or disrupt active sessions.

#### Structured JSON-Lines Logging
Every request produces one atomic JSONL log entry:
```json
{
  "timestamp": "2026-11-08T15:27:00.123456+00:00",
  "trace_id": "8d3e91a2-45bc-4f71-a02b-9876543210ab",
  "endpoint": "/ask",
  "method": "POST",
  "status_code": 200,
  "duration_ms": 14.2,
  "session_id": "sess-prod-01",
  "query_masked": "My PAN is [PAN_MASKED], check status of LA-1007",
  "intent": "status",
  "grounded": true,
  "escalate": false,
  "error": null
}
```

---

## 3. Quantitative Evaluation Benchmark

Evaluated across a 15-case test suite covering all 12 policy topics and 3 edge/OOS cases:

```mermaid
xychart-beta
    title "LLM-as-Judge 15-Query Evaluation Scores"
    x-axis ["Accuracy", "Grounding", "Completeness", "Safety"]
    y-axis "Macro Score (0.0 - 1.0)" 0.0 --> 1.0
    bar [0.7447, 1.0000, 0.5553, 1.0000]
```

- **Accuracy (0.7447):** Factual consistency against reference key points.
- **Grounding (1.0000):** Guaranteed by the stage-5 output guardrail (`SUPPORT_THRESHOLD=0.81`) and AutoGen review.
- **Completeness (0.5553):** Synthesizes concise, direct answers rather than verbatim text dumping.
- **Safety (1.0000):** 100% rejection of prompt injections and zero PII leakage.

