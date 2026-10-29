# Implementation plans

Each `NN-<slug>.md` file in this folder is a self-contained unit of work sized for one
agent session and one commit. Follow the protocol in [`AGENTS.md`](../../AGENTS.md).

- Status tracker: [`PROGRESS.md`](PROGRESS.md)
- Shared values produced/consumed by plans: [`DECISIONS.md`](DECISIONS.md)
- Environment: [`../SETUP.md`](../SETUP.md)
- Full brief (requirements): [`../BRIEF.md`](../BRIEF.md)

## Plan doc template
Every plan doc has these sections, in this order:

| Section | Content |
|---|---|
| **Goal** | One paragraph: what exists after this plan. |
| **Brief tasks** | Which capstone tasks (T1–T16) and acceptance bullets this plan satisfies. |
| **Depends on** | Plan IDs that must be `done`. |
| **Read first** | Files and `DECISIONS.md` keys to read before starting. |
| **Files** | Every file to create (`+`) or modify (`~`). |
| **Code changes** | Per file: signatures, constants, algorithms, reference snippets. |
| **Tests** | Test file(s) and named test cases with what each asserts. |
| **Steps** | `- [ ]` checklist. Tick as you go. |
| **Verify** | Exact commands + expected results. All must pass before `done`. |
| **Record in DECISIONS.md** | Keys this plan must write. |
| **Pitfalls** | Known traps for this plan. |
| **Commit** | Exact commit message. |

## Dependency graph
```
00 → 01 → 06 ─────────────┐
00 → 02 → 03 → 04 → 05    │
               04 ────────┼→ 08 → 10 ─┐
00 → 07 ──────────────────┘   08 → 12 ─┤
               04 → 09 ─→ 13 (+07) ────┤
               04 → 11 ────────────────┴→ 14 → 15 ─┐
                                          14 → 16 ─┴→ 17
```
`PROGRESS.md`'s `Deps` column is authoritative if this drawing ever disagrees.
Plans on different branches of the graph (e.g. 01/02/07, or 05/06/09/11) can be done in
any order or in parallel by different agents, as long as each commits separately.

## Coverage — brief task → plan
| Task | Requirement | Plan |
|---|---|---|
| T1 | Seeded dataset, ≥40 records, category/status/fraud thresholds | 01 |
| T2 | ≥12 KB docs, every required topic | 02 |
| T3 | Fixed+overlap and sentence chunking, two Chroma collections | 03 |
| T4 | Grounded generation, calibrated IDK threshold, 5+1 demo | 04 |
| T5 | Doc-level P/R per collection, recommendation | 05 |
| T6 | `check_loan_application_status` + designed escalation score | 06 |
| — | MockLLM (BaseLLM) + real-LLM factory | 07 |
| T7 | CrewAI crew ≥3 agents, both tools invoked via `kickoff()` | 08 |
| T9 | Pydantic structured output validated in code | 08 |
| T10 | PII masking, injection detection, groundedness refusal | 09 |
| T15 | Least autonomy, risk classification, budget cap | 10 |
| T16 | Response cache with hit evidence | 11 |
| T8 | LangChain session memory, carry + fresh transcripts | 12 |
| T14 | Autogen RoundRobinGroupChat review, approve + revise | 13 |
| — | End-to-end pipeline used by demos/API/eval | 14 |
| T11 | FastAPI ≥2 HTTP + 1 WebSocket, disconnect-safe | 15 |
| T12 | JSONL logs with trace ID, masked PII | 15 |
| T13 | 15-query LLM-as-judge eval, 4 scores + averages | 16 |
| — | `run_all` transcripts, final README (track, choices, numbers) | 17 |

## Global conventions (apply to every plan)
- Package root: `credobot/` (with `__init__.py` in every sub-package). `dataset.py` and
  `kb/` live at repo root because the brief names them.
- First import in every entry point / module that touches crewai, chromadb, autogen or
  sentence-transformers: `from credobot import config  # noqa: F401` (sets env defaults).
- Demo modules write markdown transcripts via `credobot.demos.transcript.Transcript`
  (created in plan 00) so output format is uniform.
- Tests use `tmp_path` for Chroma/log dirs via the `isolated_env` fixture in
  `tests/conftest.py` (created in plan 00, extended in later plans).
- Call/invocation counters (LLM calls, Chroma queries, tool invocations) live in
  `credobot.counters` (created in plan 00) and are used as evidence in transcripts.
