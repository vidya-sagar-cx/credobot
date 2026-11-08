# Plan 08 — CrewAI crew & structured output

## Goal
A 3-agent sequential CrewAI crew (Retrieval Agent → Lookup Agent → Response Composer)
run via `.kickoff()`, using the deployed RAG collection and the loan-status tool, whose
final output always validates against a Pydantic `CrewResponse`.

## Brief tasks
T7, T9. Acceptance: "crew has ≥3 agents …; both the RAG tool and the
`check_loan_application_status` tool are demonstrably invoked on different queries via
`.kickoff()`" and "Every crew response validates against a declared Pydantic
structured-output schema."

## Depends on
04 (`grounded_answer`), 06 (`check_loan_application_status`), 07 (`MockLLM`, `react`)

## Read first
`credobot/rag/generate.py`, `credobot/tools/loan_status.py`, `credobot/llm/mock_llm.py`,
`credobot/llm/react.py`, DECISIONS `deploy_collection`, `idk_threshold`, `escalation_threshold`.

## Files
```
+ credobot/crew/schemas.py
+ credobot/tools/rag_tool.py
+ credobot/tools/crew_tools.py      # CrewAI BaseTool wrappers
+ credobot/crew/agents.py
+ credobot/crew/crew.py
~ credobot/llm/mock_llm.py          # implement compose()
+ tests/test_crew.py
+ transcripts/part2_crew.md         (generated)
```

## Code changes

### `credobot/crew/schemas.py`
```python
class LoanStatus(BaseModel):
    record_id: str; category: str; status: str; loan_amount_inr: int
    days_since_created: int; flagged_for_fraud_review: bool
    escalation_score: float = Field(ge=0, le=1); escalate: bool

Intent = Literal["policy", "status", "mixed", "refused", "unknown"]

class CrewResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    answer: str = Field(min_length=1)
    intent: Intent
    sources: list[str] = []          # KB doc_ids used
    record: LoanStatus | None = None
    escalate: bool = False
    grounded: bool
    top_similarity: float | None = None
    guardrail_events: list[str] = []

def validate_response(raw: str | dict | BaseModel) -> CrewResponse:
    """Single validation entry point used everywhere (crew, pipeline, API)."""
```

### `credobot/tools/rag_tool.py`
`rag_lookup(query: str) -> str` — calls `grounded_answer(query, config.DEPLOY_COLLECTION)`
and returns a JSON string `{"answer", "sources", "grounded", "fallback", "top_similarity",
"context": [chunk texts]}`; `counters.incr("tool.rag_lookup")`. Plan 11 wraps
`grounded_answer` with the cache — keep the call site a single line so that's trivial.

### `credobot/tools/crew_tools.py`
```python
class RagLookupInput(BaseModel):  query: str = Field(..., description="The user's policy question")
class LoanStatusInput(BaseModel): record_id: str = Field(..., description="Loan application id like LA-1001")

class RagLookupTool(BaseTool):
    name: str = "rag_lookup"                  # deliberately contains 'lookup' (pitfall 2)
    description: str = "Search the X Corp policy knowledge base and return a grounded answer."
    args_schema: type[BaseModel] = RagLookupInput
    def _run(self, query: str) -> str: return rag_lookup(query)

class LoanStatusTool(BaseTool):
    name: str = "check_loan_application_status"
    description: str = "Look up a loan application's status, amount and escalation score."
    args_schema: type[BaseModel] = LoanStatusInput
    def _run(self, record_id: str) -> str: return json.dumps(check_loan_application_status(record_id))
```

### `credobot/crew/agents.py`
```python
RETRIEVAL_ROLE, LOOKUP_ROLE, COMPOSER_ROLE = "Retrieval Agent", "Lookup Agent", "Response Composer"
def build_agents(llm=None) -> dict[str, Agent]:
    llm = llm or factory.get_crew_llm()
    retrieval = Agent(role=RETRIEVAL_ROLE, goal=..., backstory=..., tools=[RagLookupTool()],
                      llm=llm, allow_delegation=False, max_iter=3, verbose=False)
    lookup    = Agent(role=LOOKUP_ROLE, ..., tools=[LoanStatusTool()], ...)
    composer  = Agent(role=COMPOSER_ROLE, ..., tools=[], ...)
```
`allow_delegation=False` on all (delegation tools would let agents reach others' tools).
Plan 10 will route agent construction through a governance `make_agent`; keep
`build_agents` as the single construction site.

### `credobot/crew/crew.py`
```python
def build_tasks(query: str, agents, history_note: str = "") -> list[Task]:
    t_retrieve = Task(description=f"Answer the policy part of the question using rag_lookup.\n<<QUERY>>{query}<</QUERY>>",
                      expected_output="JSON returned by rag_lookup", agent=agents[RETRIEVAL_ROLE])
    t_lookup   = Task(description=f"If the question mentions a loan application id, look it up; "
                      f"otherwise answer NO_RECORD_ID.\n<<QUERY>>{query}<</QUERY>>",
                      expected_output="JSON record or NO_RECORD_ID", agent=agents[LOOKUP_ROLE])
    t_compose  = Task(description=f"<<ROLE:composer>> Combine the retrieval and lookup results "
                      f"into one answer.\n<<QUERY>>{query}<</QUERY>>{history_note}",
                      expected_output="CrewResponse JSON", agent=agents[COMPOSER_ROLE],
                      context=[t_retrieve, t_lookup], output_pydantic=CrewResponse)
    return [t_retrieve, t_lookup, t_compose]

def build_crew(query, llm=None, history_note="") -> Crew:
    agents = build_agents(llm)
    return Crew(agents=list(agents.values()), tasks=build_tasks(query, agents, history_note),
                process=Process.sequential, verbose=False)

@dataclass
class CrewRun:
    response: CrewResponse; retrieval_raw: str; lookup_raw: str
    tool_calls: dict[str, int]; llm_calls: int

def run_crew(query: str, history_note: str = "") -> CrewRun:
    before = counters.snapshot()
    out = build_crew(query, history_note=history_note).kickoff()
    resp = validate_response(out.pydantic or out.raw)       # always validate in code
    ...diff counters → tool_calls / llm_calls
```

### `MockLLM.compose()` (in `mock_llm.py`)
Read the two prior task outputs from the Composer prompt (CrewAI puts context under a
"This is the context you're working with:" section). Parse the retrieval JSON and the
lookup JSON / `NO_RECORD_ID`, then build a `CrewResponse` dict:
- intent: `status` if record and retrieval fell back; `policy` if no record;
  `mixed` if both; `unknown` if both empty.
- answer: policy answer text (if not fallback) + one status sentence, e.g.
  `"Application LA-1007 (Home Loan, ₹45,00,000) is Under Review. Escalation score 0.78 —
  escalated to lending operations."`
- sources, grounded (= retrieval grounded or status-only), top_similarity, record, escalate.
Return `json.dumps(...)`. If `response_model` is passed, return a string that
`response_model.model_validate_json` accepts.

### Demo (`python -m credobot.crew.crew`) → `transcripts/part2_crew.md`
Three queries via `run_crew`:
1. Policy-only: "What documents do I need for KYC?" → `tool.rag_lookup` = 1, lookup tool 0.
2. Status-only: "What is the status of application LA-10xx?" (pick an escalated record id
   from plan 06's transcript) → lookup tool = 1.
3. Mixed: "Can I prepay my loan LA-10yy without penalty?" → both tools = 1.
For each: query, per-agent raw outputs, tool invocation counts, validated `CrewResponse`
JSON, and "schema validation: PASS".

## Tests — `tests/test_crew.py` (isolated_env, MOCK_LLM)
- `test_crew_has_three_agents_with_expected_tools` — roles exact; Retrieval has only
  `rag_lookup`; Lookup has only `check_loan_application_status`; Composer has none.
- `test_policy_query_invokes_rag_tool` — counters `tool.rag_lookup == 1`,
  `tool.check_loan_application_status == 0`, intent `policy`, sources non-empty.
- `test_status_query_invokes_lookup_tool` — lookup counter 1, `record.record_id` matches,
  `escalate` equals plan-06 tool output.
- `test_mixed_query_invokes_both`.
- `test_every_response_validates` — for 5 varied queries `validate_response` succeeds and
  returns `CrewResponse`; also `CrewResponse.model_validate_json(resp.model_dump_json())`.
- `test_invalid_payload_rejected` — `validate_response('{"answer": ""}')` raises `ValidationError`.
- `test_oos_query_unknown_intent` — OOS question → answer contains IDK message, grounded False.

## Steps
- [x] `schemas.py`
- [x] `rag_tool.py`, `crew_tools.py`
- [x] `agents.py`, `crew.py`
- [x] `MockLLM.compose()`
- [x] Demo + transcript
- [x] Tests; Verify; PROGRESS; commit

## Verify
1. `uv run python -m credobot.crew.crew` → 3 runs, transcript shows `rag_lookup` invoked on
   the policy query and `check_loan_application_status` on the status query, each response
   "schema validation: PASS".
2. `uv run pytest tests/test_crew.py -q` → pass.
3. No network access needed (telemetry env vars set by config).

## Record in DECISIONS.md
Nothing new.

## Pitfalls
- CrewAI tool-usage caching: CrewAI may cache identical tool calls within an agent; keep
  `cache=False` on tools or the crew if counters disagree, and note it.
- Make sure `config` is imported before `crewai` in every module (telemetry).
- `output_pydantic` makes CrewAI attempt conversion; MockLLM's JSON must already be valid.

## Commit
`plan 08: three-agent CrewAI crew with RAG and loan-status tools and CrewResponse schema`
