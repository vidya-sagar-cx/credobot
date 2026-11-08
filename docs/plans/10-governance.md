# Plan 10 — Governance: least autonomy, risk classification, runtime budget cap

## Goal
Application-layer least-autonomy enforcement (only the Lookup Agent may hold/call
`check_loan_application_status`), a documented High/Medium/Low risk classification, and a
runtime per-request token/cost budget cap that rejects oversized requests before any LLM
or tool call.

## Brief tasks
T15. Acceptance: "Least-autonomy enforcement is demonstrated (only the Lookup Agent can
call the lookup tool); a risk classification with justification is given; a runtime
cost-budget cap correctly rejects an oversized simulated request."

## Depends on
08 (`build_agents`, tool classes, roles)

## Read first
`credobot/crew/agents.py`, `credobot/crew/crew.py`, `credobot/tools/crew_tools.py`.

## Files
```
+ credobot/governance/tool_policy.py
+ credobot/governance/budget.py
+ credobot/governance/risk.md
+ credobot/governance/demo.py
~ credobot/crew/agents.py            # construct agents via make_agent
~ credobot/crew/crew.py              # assert_least_autonomy in build_crew
~ credobot/tools/crew_tools.py       # runtime caller check in LoanStatusTool._run
~ credobot/config.py                 # budget constants
+ tests/test_governance.py
+ transcripts/part4_governance.md    (generated)
```

## Code changes

### `credobot/governance/tool_policy.py`
```python
TOOL_ACL: dict[str, frozenset[str]] = {
    "check_loan_application_status": frozenset({"Lookup Agent"}),
    "rag_lookup": frozenset({"Retrieval Agent"}),
}
class ToolPermissionError(PermissionError): ...

def check_tool_assignment(role: str, tools) -> None:
    """Raise ToolPermissionError if any tool's ACL excludes `role`. Tools not in the ACL
    are denied by default (deny-by-default)."""

def make_agent(*, role: str, tools: list, **kwargs) -> Agent:
    check_tool_assignment(role, tools); return Agent(role=role, tools=tools, **kwargs)

def assert_least_autonomy(crew: Crew) -> None:
    """Re-check every agent after crew construction (defence in depth against someone
    appending tools later) and that allow_delegation is False for all agents."""
```
Layer 3 (runtime): `LoanStatusTool` gets a `allowed_role: str = "Lookup Agent"` and the
owning agent's role is bound when `make_agent` attaches it (`tool.bound_role = role`);
`_run` raises `ToolPermissionError` if `bound_role` not in `TOOL_ACL[self.name]`. This
makes the restriction hold even if a tool instance is smuggled onto another agent after
construction.

### `credobot/governance/budget.py`
```python
class BudgetExceededError(Exception):
    def __init__(self, estimate: "BudgetEstimate"): ...

@dataclass
class BudgetEstimate:
    input_tokens: int; context_tokens: int; output_tokens: int
    total_tokens: int; cost_usd: float; limit_tokens: int; limit_cost_usd: float
    @property
    def within(self) -> bool

def estimate_tokens(text: str) -> int:       # ceil(len(text) / 4), deterministic, no tokenizer download
def estimate_request(query: str) -> BudgetEstimate:
    """input = query tokens + fixed prompt overhead (PROMPT_OVERHEAD_TOKENS per agent × 3
    agents + reviewer 2) ; context = TOP_K × max chunk tokens ; output = MAX_OUTPUT_TOKENS.
    cost = total/1000 × PRICE_PER_1K_TOKENS_USD."""
def enforce_budget(query: str) -> BudgetEstimate:   # raise BudgetExceededError if not within
```
Config (env-overridable): `MAX_REQUEST_TOKENS` (e.g. 6000), `MAX_REQUEST_COST_USD`
(e.g. 0.01), `PRICE_PER_1K_TOKENS_USD` (nominal, e.g. 0.0006 — document it is a
simulated price), `PROMPT_OVERHEAD_TOKENS`, `MAX_OUTPUT_TOKENS`, and `MAX_QUERY_CHARS`
(hard cap, e.g. 4000). Choose values so every normal query (≤500 chars) passes with
≥3× headroom and a 20,000-char request fails; record the exact numbers.

`enforce_budget` is called by the pipeline (plan 14) **before** guardrails' embedding
work, crew kickoff or any LLM call. Plan 14 wires it; this plan unit-tests it directly and
also wraps `run_crew` demo calls with it.

### `credobot/governance/risk.md`
Content (also copied into README by plan 17):
- **Risk level: High.** Justification paragraph: processes financial data (loan amounts,
  application status, fraud flags) and fixed-format identity PII (PAN/Aadhaar/account
  numbers); outputs inform members' financial decisions; errors could mislead on credit
  terms or leak PII — matches the brief's "High: financial data" class even though the
  interaction shape resembles Medium-class customer support.
- Four-layer model table: Application (least autonomy ACL, guardrails, structured output,
  review stage), Runtime (budget cap, cache, IDK threshold, max_iter/max_turns), Data
  (fabricated data only, PII masking in prompts and logs), Organisational/Human (escalation
  score routes to lending ops, human review for escalated cases, audit logs w/ trace IDs).
- The one-paragraph explanation of the least-autonomy guard (3 layers: never wired;
  construction-time ACL check; runtime bound-role check).

### Demo (`python -m credobot.governance.demo` → `transcripts/part4_governance.md`)
1. Table of agents → tools as built (Lookup Agent is the only holder).
2. Attempt `make_agent(role="Response Composer", tools=[LoanStatusTool()])` → show
   `ToolPermissionError` message.
3. Attempt post-construction smuggling: append tool to composer.tools, call
   `assert_least_autonomy(crew)` → error; call the tool's `_run` with bound role composer → error.
4. Risk classification paragraph.
5. Budget: normal query estimate (within) vs 20,000-char query → `BudgetExceededError`
   with the estimate shown; `counters.snapshot()` before/after identical (no LLM/tool calls).

## Tests — `tests/test_governance.py`
- `test_only_lookup_agent_has_status_tool` (from `build_agents`).
- `test_wiring_status_tool_to_composer_blocked` and `..._to_retrieval_blocked`.
- `test_unknown_tool_denied_by_default`.
- `test_assert_least_autonomy_detects_smuggled_tool`.
- `test_runtime_bound_role_check`.
- `test_delegation_disabled`.
- `test_budget_normal_query_within`.
- `test_budget_oversized_rejected` — 20k chars → raises; error carries estimate.
- `test_budget_rejection_before_llm` — wrap a fake run: counters unchanged after rejection.
- `test_risk_doc_states_high`.

## Steps
- [x] `tool_policy.py`; refactor `agents.py` to use `make_agent`; `assert_least_autonomy` in `build_crew`
- [x] Runtime bound-role check in `LoanStatusTool`
- [x] `budget.py` + config constants
- [x] `risk.md`
- [x] Demo + transcript; tests
- [x] Re-run `tests/test_crew.py` (no regressions)
- [x] Verify; DECISIONS; PROGRESS; commit

## Verify
1. `uv run python -m credobot.governance.demo` → all 5 sections; both blocks raise; budget
   rejection shown with unchanged counters.
2. `uv run pytest tests/test_governance.py tests/test_crew.py -q` → pass.

## Record in DECISIONS.md
`max_request_tokens`, `max_request_cost_usd`, `price_per_1k_tokens_usd`, `risk_level`.

## Pitfalls
- CrewAI may copy tools when building the executor — bind role on the instance you pass
  *and* verify `_run` sees it (test it through a real kickoff).
- Don't let delegation tools (`allow_delegation=True`) open an indirect path to the lookup tool.

## Commit
`plan 10: least-autonomy tool ACL, risk classification and request budget cap`
