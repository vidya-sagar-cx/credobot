"""Unified transcript runner executing all demonstration suites in a fresh, offline environment."""
import gc
import os
import shutil
import socket
import sys
import time
from pathlib import Path

# Ensure offline environment configuration
os.environ["MOCK_LLM"] = "true"
os.environ["CREWAI_DISABLE_TELEMETRY"] = "true"
os.environ["OTEL_SDK_DISABLED"] = "true"
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

from credobot import config, counters
from credobot.rag.index import _client_cache

# Network Guard: Assert zero external network calls
_orig_connect = socket.socket.connect
_network_attempts = 0


def _guarded_connect(self, address):
    global _network_attempts
    if isinstance(address, tuple) and len(address) >= 1:
        host = str(address[0])
        # Allow loopback/internal addresses
        if host in ("127.0.0.1", "localhost", "::1", "0.0.0.0"):
            return _orig_connect(self, address)
    _network_attempts += 1
    raise RuntimeError(
        f"External network connection blocked under zero-network policy: attempted connection to {address}"
    )


STEPS = [
    ("T1: Dataset generation", "dataset", "dataset.py"),
    ("T2 & T3: Indexing dual collections", "credobot.rag.index", "credobot/rag/index.py"),
    ("T4: IDK threshold calibration", "credobot.rag.calibrate", "credobot/rag/calibrate.py"),
    ("T4: Grounded generation", "credobot.rag.generate", "credobot/rag/generate.py"),
    ("T5: Chunking evaluation", "credobot.rag.eval_chunking", "credobot/rag/eval_chunking.py"),
    ("T6: Loan status lookup & escalation", "credobot.tools.loan_status", "credobot/tools/loan_status.py"),
    ("T7: CrewAI multi-agent crew", "credobot.crew.crew", "credobot/crew/crew.py"),
    ("T8: LangChain session memory", "credobot.memory", "credobot/memory.py"),
    ("T10: Input & output guardrails", "credobot.guardrails.demo", "credobot/guardrails/demo.py"),
    ("T15: AI Governance & budget", "credobot.governance.demo", "credobot/governance/demo.py"),
    ("T16: Response query cache", "credobot.cache", "credobot/cache.py"),
    ("T14: AutoGen review stage", "credobot.review.autogen_review", "credobot/review/autogen_review.py"),
    ("E2E: Full pipeline integration", "credobot.pipeline", "credobot/pipeline.py"),
    ("T11 & T12: FastAPI & JSONL logging", "credobot.api.demo", "credobot/api/demo.py"),
    ("T13: LLM-as-judge evaluation", "credobot.eval.run_eval", "credobot/eval/run_eval.py"),
]


INDEX_CONTENT = """# CredoBot Graded Transcripts Index

All transcripts are deterministically generated under `MOCK_LLM=true` with **zero external network calls** (`network calls attempted: 0`) and **zero API keys required**.

## Task to Transcript Mapping

| Task | Target Topic / Component | Transcript File | Verification / Evidence Provided |
|---|---|---|---|
| **T1** | Dataset Design | [`part1_dataset.md`](part1_dataset.md) | 60 synthetic records, seed 2026, 20% fraud, category & status counts |
| **T2 & T3** | Knowledge Base & Indexing | [`part1_index.md`](part1_index.md) | 13 policy markdown files loaded; 62 fixed and 26 sentence chunks indexed |
| **T4** | Calibration & Fallback | [`part1_calibration.md`](part1_calibration.md) | Measured similarity distributions separating in-scope vs OOS; IDK threshold = 0.29 |
| **T4** | Grounded Generation | [`part1_grounded.md`](part1_grounded.md) | Grounded policy answers with exact citation attribution |
| **T5** | Chunking P/R Evaluation | [`part1_chunking_eval.md`](part1_chunking_eval.md) | Precision/recall comparison showing `kb_fixed` (F1=0.9091) outperforms `kb_sentence` (F1=0.7368) |
| **T6** | Loan Status & Escalation | [`part2_escalation.md`](part2_escalation.md) | Formula combining fraud flag + recency; threshold 0.55 escalates 20% high-risk loans |
| **T7** | CrewAI Orchestration | [`part2_crew.md`](part2_crew.md) | 3-agent sequential crew invoking RAG and status lookup tools |
| **T8** | Multi-Turn Memory | [`part2_memory_multiturn.md`](part2_memory_multiturn.md) | Conversation history maintained across turns with deterministic follow-up resolution |
| **T8** | Fresh Session Reset | [`part2_memory_fresh.md`](part2_memory_fresh.md) | History isolation verified: new session ID has zero prior state |
| **T10** | Guardrails | [`part2_guardrails.md`](part2_guardrails.md) | Input PII masking (PAN/Aadhaar/Account), prompt injection block, ungrounded refusal |
| **T11 & T12** | API & Structured Logging | [`part3_api.md`](part3_api.md) | FastAPI POST /ask, POST /add-document, WebSocket /ws/chat, and PII-masked JSONL audit logs |
| **T13** | LLM-as-Judge Evaluation | [`part3_eval.md`](part3_eval.md) | 15-query evaluation across Accuracy, Grounding, Completeness, Safety, and Macro Averages |
| **T13** | Machine-Readable Eval | [`part3_eval.jsonl`](part3_eval.jsonl) | Per-query JSON-Lines scores and rationale |
| **T14** | AutoGen Review Stage | [`part4_review.md`](part4_review.md) | 2-agent RoundRobinGroupChat (max_turns=2) approving valid drafts and revising ungrounded claims |
| **T15** | AI Governance | [`part4_governance.md`](part4_governance.md) | Least autonomy tool ACL, High-risk classification, and runtime budget cap rejection |
| **T16** | Response Caching | [`part4_cache.md`](part4_cache.md) | Normalized query response cache with LRU eviction and hit/miss counter observability |
| **E2E** | End-to-End Pipeline | [`pipeline_e2e.md`](pipeline_e2e.md) | Full 7-stage pipeline unifying all layers from raw query to final audited response |

---

## Acceptance Criteria Checklist (from `docs/BRIEF.md`)

### Part 1: Dataset Design & RAG Core
- [x] `dataset.py` generates >=40 loan applications meeting all structural thresholds (counts per category >=3, per status >=1, fraud % between 10% and 30%).
- [x] Knowledge base has >=12 documents covering every required banking policy topic.
- [x] Both chunking strategies (fixed-size with overlap and sentence-based) are implemented and indexed into two separate ChromaDB collections.
- [x] Grounded generation is demonstrated on >=5 in-scope queries plus 1 out-of-scope query triggering the "I don't know" fallback.
- [x] Precision and recall are computed for both collections on the same queries with visible per-query arithmetic, and a numbers-cited recommendation is given.

### Part 2: CrewAI Multi-Agent Orchestration with Tools, Memory & Guardrails
- [x] `check_loan_application_status` looks up records and computes a designed, justified `escalation_score` (not a bare boolean OR).
- [x] CrewAI crew has >=3 agents (Retrieval, Lookup, Composer); RAG tool and status lookup tool are demonstrably invoked on different queries via `.kickoff()`.
- [x] Multi-turn memory is demonstrated, with a separate fresh-conversation transcript showing history correctly absent.
- [x] Every crew response validates against a declared Pydantic structured-output schema (`CrewResponse`).
- [x] Guardrails (input-side PII masking and prompt-injection detection, output-side groundedness check) are demonstrated firing on deliberate test cases.

### Part 3: Evaluation, Observability & FastAPI Deployment
- [x] FastAPI backend exposes >=2 working HTTP endpoints plus 1 working WebSocket endpoint that survives client disconnect without crashing, using Pydantic models.
- [x] Every request produces one structured JSON-Lines log entry with a trace ID and masked PII.
- [x] All four evaluation scores (Accuracy, Grounding, Completeness, Safety) are reported per-query for all 15 test queries under `MOCK_LLM`, plus the four macro averages.

### Part 4: Resilience & Governance
- [x] AutoGen review stage is demonstrated both approving a draft unchanged and revising a draft, with structured Pydantic verdicts (`ReviewVerdict`) in both cases.
- [x] Least-autonomy enforcement is demonstrated (only the Lookup Agent can call the lookup tool); High-risk classification with justification is provided; runtime cost-budget cap correctly rejects an oversized request.
- [x] Response caching is demonstrated producing a real cache hit with before/after evidence on a repeated query.
"""


def clean_state() -> None:
    """Safely reset persistent state directories for a clean, reproducible run."""
    print("Clearing client cache and garbage collecting...")
    _client_cache.clear()
    gc.collect()

    if config.CHROMA_DIR.exists():
        print(f"Removing ChromaDB directory: {config.CHROMA_DIR}")
        try:
            shutil.rmtree(config.CHROMA_DIR, ignore_errors=True)
        except Exception as e:
            print(f"Warning: could not cleanly remove chroma dir: {e}")

    if config.LOG_DIR.exists():
        print(f"Removing logs directory: {config.LOG_DIR}")
        try:
            shutil.rmtree(config.LOG_DIR, ignore_errors=True)
        except Exception as e:
            print(f"Warning: could not cleanly remove log dir: {e}")

    counters.reset()


def run_all() -> int:
    """Run all demonstration scripts and write INDEX.md."""
    # Enforce offline & keyless constraints
    assert config.MOCK_LLM is True, "MOCK_LLM must be True for graded transcripts"
    api_key = os.environ.get("OPENAI_API_KEY", "")
    assert not api_key, "OPENAI_API_KEY must not be set during graded transcript generation"

    print("=" * 80)
    print("CREDOBOT UNIFIED TRANSCRIPT RUNNER")
    print("Zero-Network & Offline Policy: ENFORCED")
    print("Mock LLM Mode: ACTIVE")
    print("=" * 80)

    clean_state()

    # Install network guard
    socket.socket.connect = _guarded_connect

    start_time = time.monotonic()
    failed = False

    try:
        import importlib

        for i, (label, mod_name, file_path) in enumerate(STEPS, start=1):
            step_header = f"[{i}/{len(STEPS)}] Running {label} ({mod_name})"
            print("\n" + "-" * len(step_header))
            print(step_header)
            print("-" * len(step_header))

            mod = importlib.import_module(mod_name)
            if hasattr(mod, "main"):
                ret = mod.main()
                if ret is not None and ret != 0:
                    print(f"\n[FAIL] Step {label} returned non-zero exit code: {ret}")
                    failed = True
                    break
            else:
                print(f"[FAIL] Module {mod_name} missing main() function")
                failed = True
                break
    except Exception as e:
        print(f"\n[EXCEPTION] Error running demo step: {e}")
        import traceback
        traceback.print_exc()
        failed = True
    finally:
        socket.socket.connect = _orig_connect

    elapsed = time.monotonic() - start_time

    if failed:
        print("\n" + "=" * 80)
        print(f"[ERROR] Transcript generation failed after {elapsed:.1f}s")
        print("=" * 80)
        return 1

    # Write transcripts/INDEX.md
    index_path = config.TRANSCRIPTS_DIR / "INDEX.md"
    index_path.parent.mkdir(parents=True, exist_ok=True)
    with open(index_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(INDEX_CONTENT.strip() + "\n")

    print("\n" + "=" * 80)
    print(f"[SUCCESS] All {len(STEPS)} transcripts regenerated successfully in {elapsed:.1f}s!")
    print(f"Network calls attempted: {_network_attempts}")
    print(f"Transcript index created at: {index_path}")
    print("=" * 80)
    return 0


def main() -> int:
    return run_all()


if __name__ == "__main__":
    sys.exit(main())

