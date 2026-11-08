# Plan 17 — Regenerate all transcripts & write the final README

## Goal
One command regenerates every transcript under `MOCK_LLM` with no network, an index of
transcripts mapped to brief tasks, and a complete `README.md` that satisfies every
submission requirement — all values sourced from `DECISIONS.md` and the transcripts.

## Brief tasks
Submission requirements + README-related acceptance bullets for T1, T4, T5, T6, T15
and the telemetry confirmation.

## Depends on
15, 16 (therefore all)

## Read first
`docs/plans/DECISIONS.md` (all keys must be filled — if any is `TBD`, stop and set the
owning plan back to `in-progress` with a note), every `transcripts/*.md`,
`credobot/governance/risk.md`, `docs/BRIEF.md`.

## Files
```
+ credobot/demos/__init__.py (exists)
+ credobot/demos/run_all.py
+ transcripts/INDEX.md            (generated)
~ README.md
+ tests/test_repo_completeness.py
```

## Code changes

### `credobot/demos/run_all.py` (`python -m credobot.demos.run_all`)
- Assert `config.MOCK_LLM is True` and `OPENAI_API_KEY` is empty/unset (abort otherwise —
  graded transcripts must be mock). Set `HF_HUB_OFFLINE=1` if the model is cached.
- Optional network guard: monkeypatch `socket.socket.connect` to raise for non-loopback
  addresses for the duration of the run and report "network calls attempted: 0".
- Run in order, each in-process via its `main()`: `dataset`, `rag.index`,
  `rag.calibrate`, `rag.generate`, `rag.eval_chunking`, `tools.loan_status`,
  `crew.crew`, `memory`, `guardrails.demo`, `governance.demo`, `cache`,
  `review.autogen_review`, `pipeline`, `api.demo`, `eval.run_eval`.
- Delete `.chroma/` and `logs/` first (fresh, reproducible run).
- Write `transcripts/INDEX.md`: table Task → transcript file → one-line what it proves.
- Exit non-zero if any step fails.

### README.md structure (replace the planning-stage README)
1. Title + **"Track: Finance (Banking & FinTech)"** as the first line under the title.
2. One-paragraph overview + architecture as a text list (no images): request → budget →
   input guard → memory → CrewAI crew (Retrieval/Lookup/Composer) → output guard →
   Autogen review → response; plus logging/caching.
3. **Runs under MOCK_LLM with zero API keys** statement + **telemetry confirmation**:
   "`CREWAI_DISABLE_TELEMETRY=true` and `OTEL_SDK_DISABLED=true` are set (defaults in
   `credobot/config.py`, also in `.env.example`)."
4. Quick start (link to `docs/SETUP.md`; 4 commands).
5. **Part 1 — Dataset design** (T1): seed, n, category weights, status weights, amount
   ranges per category + one-sentence rationale, fraud probability, printed counts per
   category/status, fraud %. Reproduce command.
6. KB: list of 13 docs → topic (T2).
7. Chunking params + chunk counts (T3).
8. **IDK threshold calibration** (T4): table of measured top-1 sims (in-scope vs OOS,
   both collections), chosen threshold and why.
9. **Chunking evaluation** (T5): macro P/R for both + the 2–3 sentence recommendation
   (from DECISIONS) + link to per-query arithmetic transcript.
10. **Escalation score** (T6): exact formula, threshold, distribution justification.
11. Crew (T7), memory (T8), schema (T9), guardrails (T10) — short sections each linking
    their transcript.
12. API (T11) + logging (T12): endpoints table, sample log line (masked).
13. **Evaluation** (T13): averages table + link.
14. Review stage (T14), **governance** (T15): least-autonomy guard paragraph, **risk
    classification: High** + justification paragraph (from `risk.md`), budget cap values;
    cache (T16).
15. Optional real-LLM usage.
16. Repository layout, how to run tests, transcript index link, "AI-agent workflow" note
    linking `docs/plans/`.

### `tests/test_repo_completeness.py`
- `test_readme_mentions_track` — README contains "Finance (Banking & FinTech)".
- `test_readme_has_dataset_choices` — contains the seed value from `dataset.SEED` and
  every category weight.
- `test_readme_mentions_telemetry` — contains `CREWAI_DISABLE_TELEMETRY=true`.
- `test_readme_has_threshold` — contains `config.IDK_THRESHOLD` value.
- `test_all_transcripts_exist` — every file listed in INDEX.md exists & non-empty.
- `test_decisions_no_tbd` — `DECISIONS.md` has no `TBD`.
- `test_no_images_or_pdfs` — no `*.png|jpg|pdf|pptx|mp4` tracked (`git ls-files`).

## Steps
- [x] Confirm DECISIONS has no TBD
- [x] `run_all.py`; run it end-to-end from a clean state
- [x] Write README from DECISIONS + transcripts (no invented numbers)
- [x] `tests/test_repo_completeness.py`
- [x] Full test suite
- [x] Fresh-clone check (Verify #4)
- [x] PROGRESS → done; commit

## Verify
1. `uv run python -m credobot.demos.run_all` → exits 0; "network calls attempted: 0";
   all transcripts regenerated.
2. `uv run pytest -q` → full suite passes.
3. `git status` → only expected transcript diffs (timestamps) — commit them.
4. Fresh clone in a temp dir: `git clone <repo> x && cd x && git switch
   feat/loan-support-agent && uv sync && uv run python -m credobot.demos.run_all` works
   (on Windows too, if available — PowerShell).
5. Walk the acceptance-criteria list in `docs/BRIEF.md` and tick each against a
   transcript/README section; paste the checklist at the bottom of `transcripts/INDEX.md`.

## Record in DECISIONS.md
Nothing new.

## Pitfalls
- README numbers must match transcripts exactly; regenerate README sections from the
  same run.
- Don't commit `.chroma/`, `logs/` or `.env`.

## Commit
`plan 17: regenerate transcripts and write final README`
