# CredoBot AI Governance & Risk Assessment

## Risk Classification: High Risk

**Justification:** CredoBot operates within the retail banking and consumer lending domain, processing sensitive financial information (loan application identifiers, sanction amounts, review statuses, and compliance/fraud escalation indicators) alongside fixed-format personal identity numbers (PAN, Aadhaar, and bank account numbers). Its conversational responses directly inform customer financial planning and credit obligations. Erroneous outputs, policy misstatements, or unintended disclosures of customer identifiers represent severe operational and regulatory risks. Consequently, under standard AI risk frameworks, CredoBot is classified as **High Risk** (financial transactions and customer data), requiring strict multi-layer architectural safeguards rather than standard consumer chatbot controls.

---

## Four-Layer AI Governance Model

CredoBot enforces defense-in-depth governance across four distinct architectural tiers:

| Layer | Safeguard Mechanisms | Implementation in CredoBot |
|---|---|---|
| **Application Layer** | Least-autonomy tool ACL, input/output guardrails, structured schema enforcement, dual-agent verification. | Strict deny-by-default `TOOL_ACL` restricts core banking lookups exclusively to the Lookup Agent; PII masking redacts PAN/Aadhaar before model ingestion; prompt-injection heuristics intercept jailbreaks; Pydantic `CrewResponse` strictly typed; 2-agent AutoGen review audits claims. |
| **Runtime Layer** | Per-request budget bounds, deterministic fallbacks, iteration caps. | Pre-invocation `enforce_budget` rejects requests exceeding token, dollar cost, or query character ceilings before any LLM or vector query executes; empirical `IDK_THRESHOLD = 0.29` triggers calibrated refusals; agent execution is bounded by `max_iter=3` and `allow_delegation=False`. |
| **Data Layer** | Synthetic data isolation, sanitization of persistent traces. | Completely synthetic seeded dataset (seed 2026, N=60); zero real customer records; input PII sanitizer masks identifiers in both agent context and persistent JSON-Lines request logs. |
| **Organisational & Human Layer** | Human-in-the-loop escalation routing, tamper-evident audit trails. | Automated composite `escalation_score` (threshold 0.55) flags high-risk applications (e.g., fraud review or aged in-flight reviews) and routes them to human lending operations; every transaction logs structured JSONL entries with UUID trace IDs. |

---

## Least-Autonomy Architecture (Three-Layer Protection)

To prevent privilege escalation or tool hijacking across collaborative agents, CredoBot enforces least autonomy through three independent layers:
1. **Architectural Wiring:** The core database tool `check_loan_application_status` is wired exclusively into the `Lookup Agent`. The `Retrieval Agent` receives only `rag_lookup`, and the `Response Composer` receives zero tools. Delegation is globally disabled (`allow_delegation=False`) to prevent indirect execution.
2. **Construction-Time ACL Enforcement:** `make_agent` inspects tool assignment against `TOOL_ACL` (deny-by-default), raising `ToolPermissionError` if unauthorized tools are assigned, while `assert_least_autonomy` verifies the complete crew graph prior to kickoff.
3. **Runtime Role Binding:** Tools maintain a `bound_role` attribute set during agent attachment. In `LoanStatusTool._run()`, runtime checks verify that the caller role is explicitly authorized under `TOOL_ACL`, thwarting post-construction tool injection attempts.
