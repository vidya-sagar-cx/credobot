# Plan 07 — MockLLM (CrewAI `BaseLLM`) & LLM factory

## Goal
A deterministic, zero-network `MockLLM` that drives CrewAI's ReAct loop correctly
(including both brief-documented pitfalls), plus a factory that returns mock or real
OpenAI-compatible clients for CrewAI, plain text generation and (later) Autogen.

## Brief tasks
Submission guideline "Implementing MOCK_LLM for a CrewAI crew" (both pitfalls); enables
T7/T9. The real-LLM path is optional and off by default.

## Depends on
00

## Read first
`docs/BRIEF.md` Submission Guidelines; `credobot/config.py`; `credobot/counters.py`;
installed crewai source (versions in DECISIONS `pkg_versions`):
`crewai/llms/base_llm.py` (`BaseLLM.call` signature),
`crewai/utilities/agent_utils.py::check_native_tool_support`,
`crewai/translations/en.json` (`slices.tools`, `slices.observation`).

Facts verified at planning time (crewai 1.15.x):
- `BaseLLM` is a pydantic model; required field `model: str`; abstract method only `call`.
- `call(self, messages: str | list[LLMMessage], tools=None, callbacks=None,
  available_functions=None, from_task=None, from_agent=None, response_model=None)`.
- Native tool calling is used only if `llm.supports_function_calling()` is truthy →
  MockLLM returns `False` so CrewAI uses the text ReAct format.
- The `tools` system-prompt slice contains `Observation: the result of the action`
  (pitfall 1). Tool results are appended as text starting with `"\nObservation:"`.
Re-check these against the installed version before coding; note deviations in the doc.

## Files
```
+ credobot/llm/mock_llm.py
+ credobot/llm/react.py           # pure parsing helpers (unit-testable without crewai)
+ credobot/llm/factory.py
+ tests/test_mock_llm.py
```

## Code changes

### Prompt contract (shared with plan 08)
Every CrewAI task description built by plan 08 embeds the user question as
`<<QUERY>>…<</QUERY>>`. The Composer task also embeds `<<ROLE:composer>>`.
Agent roles are exactly: `"Retrieval Agent"`, `"Lookup Agent"`, `"Response Composer"`.

### `credobot/llm/react.py` (no crewai import)
```python
QUERY_RE = re.compile(r"<<QUERY>>(.*?)<</QUERY>>", re.S)
TOOL_BLOCK_RE   # parses CrewAI's tool description lines:
                # "Tool Name: X\nTool Arguments: {json}\nTool Description: …"

def normalize_messages(messages) -> list[dict]:   # str → [{"role":"user","content":s}]

def split_prompt_and_trace(messages) -> tuple[list[dict], list[dict]]:
    """PITFALL 1 guard. The 'prompt' is the leading system message(s) + the FIRST user
    message (task prompt, which contains the template 'Observation: the result of the
    action'). The 'trace' is everything AFTER that: our own previous assistant turns and
    the observation messages CrewAI appended. Only the trace is searched for results."""

def last_observation(trace: list[dict]) -> str | None:
    """Return the text after the last 'Observation:' that occurs in the TRACE only and
    that follows an assistant 'Action:' turn. Strip trailing CrewAI reminder text
    (anything after a blank line followed by 'Thought:'/'Remember'/'IMPORTANT')."""

def extract_query(prompt_msgs) -> str | None
def parse_tool_specs(prompt_text) -> list[ToolSpec]:   # name + arg field names from JSON schema
def choose_tool_and_args(specs, query, role) -> tuple[str, dict] | None:
    """PITFALL 2 guard: dispatch on DECLARED ARG SCHEMA, never on tool name.
    - spec whose args include 'record_id' → only if RECORD_ID_RE matches query → {"record_id": id}
    - spec whose args include 'query'     → {"query": query}
    - otherwise None. If several qualify, prefer the one whose required args are all
    satisfiable from the query. Tool names are only echoed back, never inspected."""

def format_action(tool_name, args) -> str:
    return f"Thought: I should use a tool.\nAction: {tool_name}\nAction Input: {json.dumps(args)}"
def format_final(text) -> str:
    return f"Thought: I now can give a great answer\nFinal Answer: {text}"
```
`RECORD_ID_RE` has exactly one definition: if plan 06 is done, import it from
`credobot.tools.loan_status`; otherwise define it here and plan 06 imports it from
`credobot.llm.react` (06 is pure Python, so that import is cheap). Note which in PROGRESS.

### `credobot/llm/mock_llm.py`
```python
from credobot import config  # noqa: F401  (env defaults first)
from crewai.llms.base_llm import BaseLLM

class MockLLM(BaseLLM):
    model: str = "mock-llm"
    llm_type: str = "mock"

    def supports_function_calling(self) -> bool: return False
    def supports_stop_words(self) -> bool: return True
    def get_context_window_size(self) -> int: return 128_000

    def call(self, messages, tools=None, callbacks=None, available_functions=None,
             from_task=None, from_agent=None, response_model=None):
        counters.incr("llm.crew")
        prompt, trace = react.split_prompt_and_trace(messages)
        role = getattr(from_agent, "role", None) or react.role_from_prompt(prompt)
        query = react.extract_query(prompt) or ""
        obs = react.last_observation(trace)
        if role == "Response Composer":
            return react.format_final(self.compose(prompt, response_model))
        if obs is None:
            specs = react.parse_tool_specs(prompt_text)          # or from from_agent.tools[i].args_schema
            choice = react.choose_tool_and_args(specs, query, role)
            if choice: return react.format_action(*choice)
            return react.format_final(self.no_tool_answer(role, query))  # e.g. "NO_RECORD_ID"
        return react.format_final(obs.strip())

    def compose(self, prompt, response_model) -> str:
        """Placeholder in this plan: return JSON '{}'-like stub. Plan 08 replaces this
        with the CrewResponse builder (it owns the schema). Keep the hook a method so
        plan 08 only overrides/implements it."""
```
Prefer `from_agent.tools` → `tool.args_schema.model_fields` for specs when `from_agent`
is given; fall back to parsing the prompt's `Tool Arguments:` JSON.

### `credobot/llm/factory.py`
```python
def get_crew_llm():
    if config.MOCK_LLM: return MockLLM()
    from crewai import LLM
    return LLM(model=config.LLM_MODEL, base_url=config.OPENAI_BASE_URL,
               api_key=os.environ["OPENAI_API_KEY"], temperature=0)

def get_text_llm() -> Callable[[str], str]:
    """Plain prompt → text. Mock: raises (callers use their own deterministic path).
    Real: openai-compatible chat completion via crewai.LLM(...).call(prompt)."""

def get_autogen_client():   # implemented in plan 13; stub raising NotImplementedError here
```
Missing `OPENAI_API_KEY` with `MOCK_LLM=false` → raise a clear `RuntimeError`.

## Tests — `tests/test_mock_llm.py` (no network; pure unit tests + one tiny crew)
- `test_template_observation_ignored` — **pitfall 1 regression.** Messages = [system with
  the real crewai `tools` slice text (load from `crewai/translations/en.json`), user with
  `<<QUERY>>How is EMI calculated?<</QUERY>>`] → `last_observation(trace) is None` and
  `MockLLM().call(...)` returns an `Action:` line, NOT `Final Answer: the result of the action`.
- `test_observation_after_action_used` — append assistant `Action: rag_lookup …` and a
  user `Observation: EMI uses reducing balance.` → output is
  `Final Answer: EMI uses reducing balance.`
- `test_rag_lookup_dispatched_by_schema` — **pitfall 2 regression.** Tool specs:
  `rag_lookup(query)` and `check_loan_application_status(record_id)`; query without an ID
  → chooses `rag_lookup` with `{"query": …}`; query "status of LA-1007" when only
  `rag_lookup` is available → still `{"query": …}` (never `record_id`).
- `test_tool_named_lookup_with_query_schema` — a tool named `"lookup_everything"` with a
  `query` schema gets `{"query": …}`; a tool named `"rag"` with `record_id` schema gets
  `{"record_id": "LA-1007"}`.
- `test_no_record_id_answer` — record_id-only tool + query without ID → Final Answer
  `NO_RECORD_ID` and no Action.
- `test_supports_function_calling_false`.
- `test_counter_increments` — `llm.crew` counter.
- `test_factory_mock_default` — `get_crew_llm()` is a `MockLLM`.
- `test_factory_real_requires_key(monkeypatch)` — MOCK_LLM false, no key → RuntimeError.
- `test_minimal_crew_kickoff_uses_tool` — one Agent(role="Retrieval Agent", llm=MockLLM(),
  tools=[a trivial BaseTool `echo_tool` with `args_schema` {query}]) + one Task containing
  `<<QUERY>>hi<</QUERY>>` → `Crew(...).kickoff()` output contains the echo tool's return
  value and the tool's call count is 1. (Verifies the ReAct loop end-to-end on the
  installed crewai version.)

## Steps
- [x] Re-verify crewai facts listed above against the installed version
- [x] Implement `react.py` + unit tests
- [x] Implement `MockLLM`
- [x] Implement `factory.py`
- [x] Minimal kickoff test passes
- [x] Verify; PROGRESS; commit

## Verify
1. `uv run pytest tests/test_mock_llm.py -q` → all pass (including both pitfall tests).
2. With network disabled (e.g. Wi-Fi off, or `HF_HUB_OFFLINE=1`), the minimal crew test
   still passes — proves no telemetry/network dependency.

## Record in DECISIONS.md
Nothing new (append a change-log line if crewai behaviour differed from the facts above).

## Pitfalls
- **Pitfall 1:** never search the whole conversation for `"Observation:"`.
- **Pitfall 2:** never `if "lookup" in tool_name`. Dispatch by arg schema.
- If CrewAI adds `stop=["\nObservation:"]`, your output must not contain an Observation
  line itself (CrewAI would truncate it) — only `Thought/Action/Action Input` or
  `Thought/Final Answer`.
- CrewAI may call the LLM once more after a malformed answer with an error reminder —
  keep output format exact so that never happens.

## Commit
`plan 07: deterministic MockLLM for CrewAI with pitfall guards and LLM factory`
