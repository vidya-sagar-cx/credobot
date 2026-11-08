"""Runner script for the 15-query LLM-as-judge evaluation suite."""
import json
from pathlib import Path
import statistics

from credobot import config, counters
from credobot.cache import clear_cache
from credobot.demos.transcript import Transcript
from credobot.eval.judge import JUDGE_PROMPT, JudgeScores, judge
from credobot.eval.testset import TEST_SET, assert_coverage
from credobot.memory import clear_all_sessions
from credobot.pipeline import answer


def run_evaluation() -> tuple[list[dict], dict[str, float]]:
    """Execute evaluation over all 15 test cases and compute metric averages."""
    assert_coverage()
    clear_cache()
    clear_all_sessions()

    results: list[dict] = []
    accuracies: list[float] = []
    groundings: list[float] = []
    completenesses: list[float] = []
    safeties: list[float] = []

    for case in TEST_SET:
        print(f"Evaluating {case.id} [{case.topic}]: '{case.query[:50]}...'")
        pipe_res = answer(query=case.query)
        scores = judge(case, pipe_res)

        accuracies.append(scores.accuracy)
        groundings.append(scores.grounding)
        completenesses.append(scores.completeness)
        safeties.append(scores.safety)

        record = {
            "id": case.id,
            "topic": case.topic,
            "kind": case.kind,
            "query_masked": pipe_res.query_masked,
            "intent": pipe_res.response.intent,
            "grounded": pipe_res.response.grounded,
            "escalate": pipe_res.response.escalate,
            "sources": pipe_res.response.sources,
            "answer": pipe_res.response.answer,
            "accuracy": scores.accuracy,
            "grounding": scores.grounding,
            "completeness": scores.completeness,
            "safety": scores.safety,
            "rationale": scores.rationale,
        }
        results.append(record)

    averages = {
        "accuracy": round(statistics.mean(accuracies), 4),
        "grounding": round(statistics.mean(groundings), 4),
        "completeness": round(statistics.mean(completenesses), 4),
        "safety": round(statistics.mean(safeties), 4),
    }

    return results, averages


def main() -> int:
    results, averages = run_evaluation()

    if len(results) != 15:
        print(f"Error: Expected 15 evaluation cases, got {len(results)}", flush=True)
        return 1

    # Write machine-readable JSONL
    jsonl_path = config.TRANSCRIPTS_DIR / "part3_eval.jsonl"
    jsonl_path.parent.mkdir(parents=True, exist_ok=True)
    with open(jsonl_path, "w", encoding="utf-8", newline="\n") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    # Generate Markdown transcript
    t = Transcript("part3_eval", "Part 3 — LLM-as-Judge Evaluation (15 Queries)")
    t.para(
        "Quantitative evaluation of the CredoBot loan-support pipeline across 15 comprehensive "
        "test cases covering all 12 required KB topics plus out-of-scope, PII, and injection edge cases. "
        "Each query is evaluated across four core dimensions: **Accuracy**, **Grounding**, "
        "**Completeness**, and **Safety**."
    )

    t.h2("1. Evaluation Summary & Macro Averages")
    t.kv(
        {
            "Mean Accuracy": f"{averages['accuracy']:.4f}",
            "Mean Grounding": f"{averages['grounding']:.4f}",
            "Mean Completeness": f"{averages['completeness']:.4f}",
            "Mean Safety": f"{averages['safety']:.4f}",
            "Total Evaluated Queries": len(results),
            "LLM Judge Calls (llm.judge)": counters.get("llm.judge"),
        }
    )

    t.h2("2. Per-Query Evaluation Scorecard")
    table_headers = [
        "ID",
        "Topic",
        "Query",
        "Intent",
        "Answer (Excerpt)",
        "Acc",
        "Gnd",
        "Cmp",
        "Sft",
    ]
    table_rows = []
    for r in results:
        short_ans = (r["answer"][:100] + "...") if len(r["answer"]) > 100 else r["answer"]
        short_ans = short_ans.replace("\n", " ")
        short_q = (r["query_masked"][:45] + "...") if len(r["query_masked"]) > 45 else r["query_masked"]
        table_rows.append(
            [
                r["id"],
                r["topic"][:20],
                short_q,
                r["intent"],
                short_ans,
                f"{r['accuracy']:.2f}",
                f"{r['grounding']:.2f}",
                f"{r['completeness']:.2f}",
                f"{r['safety']:.2f}",
            ]
        )

    # Append averages row
    table_rows.append(
        [
            "**AVG**",
            "**All Topics**",
            "—",
            "—",
            "—",
            f"**{averages['accuracy']:.2f}**",
            f"**{averages['grounding']:.2f}**",
            f"**{averages['completeness']:.2f}**",
            f"**{averages['safety']:.2f}**",
        ]
    )
    t.table(table_headers, table_rows)

    t.h2("3. Required KB Topic Coverage")
    topic_map: dict[str, list[str]] = {}
    for r in results:
        topic_map.setdefault(r["topic"], []).append(r["id"])

    cov_headers = ["Topic", "Test Case IDs", "Status"]
    cov_rows = [
        [topic, ", ".join(ids), "COVERED"]
        for topic, ids in sorted(topic_map.items())
    ]
    t.table(cov_headers, cov_rows)

    t.h2("4. Judge Prompt Template & Scoring Rationale")
    t.para(
        "Under `MOCK_LLM=true`, the deterministic judge reads strictly the delimited sections "
        "(`<<QUESTION>>`, `<<EXPECT_REFUSAL>>`, `<<KEY_POINTS>>`, `<<CONTEXT>>`, `<<ANSWER>>`)."
    )
    t.code(JUDGE_PROMPT.strip())

    md_path = t.save()
    print(f"\n[OK] Machine-readable results saved to: {jsonl_path}")
    print(f"[OK] Evaluation transcript saved to: {md_path}")
    print(f"[OK] Macro Averages: {averages}")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())

