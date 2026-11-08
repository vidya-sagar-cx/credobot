# Part 4 — AI Governance & Risk Management

- Generated: 2026-11-08T08:48:32.161923+00:00
- MOCK_LLM: True
- CREWAI_DISABLE_TELEMETRY: true
- OTEL_SDK_DISABLED: true

## AI Governance Framework

CredoBot implements a defense-in-depth governance structure incorporating application-layer least-autonomy tool ACLs, risk classification, and runtime budget limits.

## 1. Least-Autonomy Agent Tool Allocation

By design, tools are partitioned according to minimum necessity. Only the Lookup Agent holds permission to query core banking records, while delegation is strictly disabled across all agents.

| Agent Role | Assigned Tools | Delegation Enabled | Privilege Level |
| --- | --- | --- | --- |
| Retrieval Agent | rag_lookup | False | Read-only Policy RAG |
| Lookup Agent | check_loan_application_status | False | Read-only Core Banking Lookup |
| Response Composer | (None) | False | Zero-tool Synthesis |

## 2. Construction-Time Least-Autonomy ACL Block

Attempting to wire `check_loan_application_status` to the Response Composer triggers an immediate exception.

| Attempted Assignment | Status | Enforcement Exception |
| --- | --- | --- |
| Response Composer + LoanStatusTool | BLOCKED | Role 'Response Composer' is not permitted to use tool 'check_loan_application_status'. Allowed roles: ['Lookup Agent']. |

## 3. Post-Construction Smuggling & Runtime Caller Verification

If an unauthorized tool is maliciously appended to an agent post-construction, both crew-level pre-flight validation (`assert_least_autonomy`) and the tool's runtime caller check trigger refusal.

| Enforcement Point | Mechanism | Result |
| --- | --- | --- |
| Crew Pre-flight Audit | assert_least_autonomy(crew) | PASSED — Blocked: 'Role 'Response Composer' is not permitted to use tool 'check_loan_application_status'. Allowed roles: ['Lookup Agent'].' |
| Runtime Tool Invocation | LoanStatusTool._run() bound_role check | PASSED — Blocked: 'Runtime caller violation: Role 'Response Composer' cannot execute tool 'check_loan_application_status'.' |

## 4. System Risk Classification: High Risk

**Classification:** **High Risk**

**Justification:** CredoBot processes sensitive financial records (sanction amounts, underwriting statuses, and fraud review indicators) alongside fixed-format identity PII (PAN, Aadhaar, account numbers). Because outputs directly impact consumer loan sanctions and financial commitments, CredoBot requires strict defense-in-depth architectural governance over standard conversational AI controls.

## 5. Runtime Request Token & Cost Budget Cap

Incoming requests are evaluated against configured budget bounds (MAX_REQUEST_TOKENS=6000, MAX_REQUEST_COST_USD=$0.0100, MAX_QUERY_CHARS=4000). Oversized requests are dropped immediately before executing any vector retrieval or LLM inference.

| Scenario | Query Length | Estimated Tokens | Estimated Cost (USD) | Budget Decision | LLM/Tool Calls |
| --- | --- | --- | --- | --- | --- |
| Standard Query | 30 chars | 1908 | $0.00114 | ACCEPTED | Proceeds to Agent Pipeline |
| Oversized Request (24k chars) | 25200 chars | >6000 | >$0.0050 | REJECTED: 'Request character length 25200 exceeds limit 4000.' | Zero (LLM diff: 0, Tool diff: 0) |
