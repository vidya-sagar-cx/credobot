"""Empirical calibration of the RAG 'I don't know' similarity threshold."""
from typing import Any
from credobot.demos.transcript import Transcript
from credobot.rag.index import COLLECTIONS
from credobot.rag.queries import IN_SCOPE, OUT_OF_SCOPE
from credobot.rag.retrieve import retrieve, top1_similarity


def run_calibration(client: Any = None) -> dict[str, Any]:
    """Measure top-1 similarity for in-scope and out-of-scope queries across collections."""
    records: list[dict[str, Any]] = []

    for q, _ in IN_SCOPE:
        hits_fixed = retrieve(q, collection=COLLECTIONS["fixed"], client=client)
        hits_sent = retrieve(q, collection=COLLECTIONS["sentence"], client=client)
        records.append(
            {
                "query": q,
                "scope": "IN_SCOPE",
                "sim_fixed": top1_similarity(hits_fixed),
                "sim_sent": top1_similarity(hits_sent),
            }
        )

    for q in OUT_OF_SCOPE:
        hits_fixed = retrieve(q, collection=COLLECTIONS["fixed"], client=client)
        hits_sent = retrieve(q, collection=COLLECTIONS["sentence"], client=client)
        records.append(
            {
                "query": q,
                "scope": "OUT_OF_SCOPE",
                "sim_fixed": top1_similarity(hits_fixed),
                "sim_sent": top1_similarity(hits_sent),
            }
        )

    in_fixed = [r["sim_fixed"] for r in records if r["scope"] == "IN_SCOPE"]
    out_fixed = [r["sim_fixed"] for r in records if r["scope"] == "OUT_OF_SCOPE"]
    in_sent = [r["sim_sent"] for r in records if r["scope"] == "IN_SCOPE"]
    out_sent = [r["sim_sent"] for r in records if r["scope"] == "OUT_OF_SCOPE"]

    min_in_fixed, max_out_fixed = min(in_fixed), max(out_fixed)
    min_in_sent, max_out_sent = min(in_sent), max(out_sent)

    overall_min_in = min(min_in_fixed, min_in_sent)
    overall_max_out = max(max_out_fixed, max_out_sent)

    recommended_threshold = round((overall_min_in + overall_max_out) / 2.0, 2)

    return {
        "records": records,
        "fixed": {
            "min_in": min_in_fixed,
            "max_out": max_out_fixed,
            "gap": round(min_in_fixed - max_out_fixed, 4),
        },
        "sentence": {
            "min_in": min_in_sent,
            "max_out": max_out_sent,
            "gap": round(min_in_sent - max_out_sent, 4),
        },
        "overall_min_in": overall_min_in,
        "overall_max_out": overall_max_out,
        "recommended_threshold": recommended_threshold,
    }


def main() -> int:
    """Run calibration, display table and write transcript."""
    results = run_calibration()
    print("=" * 70)
    print("IDK THRESHOLD CALIBRATION RESULTS")
    print("=" * 70)
    for r in results["records"]:
        print(
            f"[{r['scope']:<12}] fixed={r['sim_fixed']:.4f} sent={r['sim_sent']:.4f} | {r['query']}"
        )

    print("\nSummary Statistics:")
    print(
        f"  kb_fixed:    min_in={results['fixed']['min_in']:.4f}, max_out={results['fixed']['max_out']:.4f}, gap={results['fixed']['gap']:.4f}"
    )
    print(
        f"  kb_sentence: min_in={results['sentence']['min_in']:.4f}, max_out={results['sentence']['max_out']:.4f}, gap={results['sentence']['gap']:.4f}"
    )
    print(f"  Overall:     min_in={results['overall_min_in']:.4f}, max_out={results['overall_max_out']:.4f}")
    print(f"  Recommended IDK_THRESHOLD: {results['recommended_threshold']:.2f}")
    print("=" * 70)

    t = Transcript("part1_calibration", "Part 1 — IDK Threshold Calibration")
    t.h2("Empirical Top-1 Cosine Similarity Measurements")
    rows = [
        [
            r["query"],
            r["scope"],
            f"{r['sim_fixed']:.4f}",
            f"{r['sim_sent']:.4f}",
        ]
        for r in results["records"]
    ]
    t.table(["Query", "Scope", "kb_fixed Top-1 Sim", "kb_sentence Top-1 Sim"], rows)

    t.h2("Cluster Separation and Calibrated Threshold")
    t.table(
        ["Collection", "Min In-Scope Sim", "Max Out-Of-Scope Sim", "Separation Gap"],
        [
            [
                COLLECTIONS["fixed"],
                f"{results['fixed']['min_in']:.4f}",
                f"{results['fixed']['max_out']:.4f}",
                f"{results['fixed']['gap']:.4f}",
            ],
            [
                COLLECTIONS["sentence"],
                f"{results['sentence']['min_in']:.4f}",
                f"{results['sentence']['max_out']:.4f}",
                f"{results['sentence']['gap']:.4f}",
            ],
        ],
    )
    t.para(
        f"Overall in-scope minimum is **{results['overall_min_in']:.4f}** and out-of-scope maximum is **{results['overall_max_out']:.4f}**."
    )
    t.para(
        f"The calibrated threshold separating both clusters is **`IDK_THRESHOLD = {results['recommended_threshold']:.2f}`**."
    )
    saved = t.save()
    print(f"\nTranscript written to: {saved}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
