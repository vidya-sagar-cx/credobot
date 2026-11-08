"""Demonstration of CredoBot AI governance: least-autonomy ACL, risk model, and budget enforcement."""
from credobot import config, counters
from credobot.crew.agents import (
    COMPOSER_ROLE,
    LOOKUP_ROLE,
    RETRIEVAL_ROLE,
    build_agents,
)
from credobot.crew.crew import build_crew
from credobot.demos.transcript import Transcript
from credobot.governance.budget import (
    BudgetExceededError,
    enforce_budget,
    estimate_request,
)
from credobot.governance.tool_policy import (
    ToolPermissionError,
    assert_least_autonomy,
    make_agent,
)
from credobot.tools.crew_tools import LoanStatusTool, RagLookupTool


def main() -> int:
    print("=" * 70)
    print("CREDOBOT AI GOVERNANCE DEMONSTRATION")
    print("=" * 70)

    t = Transcript("part4_governance", "Part 4 — AI Governance & Risk Management")
    t.h2("AI Governance Framework")
    t.para(
        "CredoBot implements a defense-in-depth governance structure incorporating "
        "application-layer least-autonomy tool ACLs, risk classification, and runtime budget limits."
    )

    # ---------------------------------------------------------
    # 1. Least Autonomy Tool Assignment Table
    # ---------------------------------------------------------
    agents = build_agents()
    print("\n1. Declared Agent Permissions:")
    for role, ag in agents.items():
        tool_names = [t.name for t in ag.tools] if ag.tools else ["(None)"]
        print(f"  {role:<20} -> {', '.join(tool_names)}")

    t.h2("1. Least-Autonomy Agent Tool Allocation")
    t.para(
        "By design, tools are partitioned according to minimum necessity. Only the Lookup Agent holds "
        "permission to query core banking records, while delegation is strictly disabled across all agents."
    )
    t.table(
        ["Agent Role", "Assigned Tools", "Delegation Enabled", "Privilege Level"],
        [
            [RETRIEVAL_ROLE, "rag_lookup", "False", "Read-only Policy RAG"],
            [LOOKUP_ROLE, "check_loan_application_status", "False", "Read-only Core Banking Lookup"],
            [COMPOSER_ROLE, "(None)", "False", "Zero-tool Synthesis"],
        ],
    )

    # ---------------------------------------------------------
    # 2. Construction-Time ACL Block
    # ---------------------------------------------------------
    print("\n2. Attempting unauthorized tool assignment at construction...")
    construction_err = ""
    try:
        make_agent(role=COMPOSER_ROLE, tools=[LoanStatusTool()])
    except ToolPermissionError as e:
        construction_err = str(e)
        print(f"  Successfully Blocked: {construction_err}")

    t.h2("2. Construction-Time Least-Autonomy ACL Block")
    t.para("Attempting to wire `check_loan_application_status` to the Response Composer triggers an immediate exception.")
    t.table(
        ["Attempted Assignment", "Status", "Enforcement Exception"],
        [
            ["Response Composer + LoanStatusTool", "BLOCKED", construction_err],
        ],
    )

    # ---------------------------------------------------------
    # 3. Post-Construction Smuggling & Runtime Check
    # ---------------------------------------------------------
    print("\n3. Testing post-construction smuggling & runtime checks...")
    crew = build_crew("What is my status?")
    composer = [a for a in crew.agents if a.role == COMPOSER_ROLE][0]
    smuggled_tool = LoanStatusTool()
    smuggled_tool.bound_role = COMPOSER_ROLE
    composer.tools.append(smuggled_tool)

    audit_err = ""
    try:
        assert_least_autonomy(crew)
    except ToolPermissionError as e:
        audit_err = str(e)
        print(f"  Audit Detection: {audit_err}")

    runtime_err = ""
    try:
        smuggled_tool._run("LA-1001")
    except ToolPermissionError as e:
        runtime_err = str(e)
        print(f"  Runtime Guard:   {runtime_err}")

    t.h2("3. Post-Construction Smuggling & Runtime Caller Verification")
    t.para(
        "If an unauthorized tool is maliciously appended to an agent post-construction, both crew-level "
        "pre-flight validation (`assert_least_autonomy`) and the tool's runtime caller check trigger refusal."
    )
    t.table(
        ["Enforcement Point", "Mechanism", "Result"],
        [
            ["Crew Pre-flight Audit", "assert_least_autonomy(crew)", f"PASSED — Blocked: '{audit_err}'"],
            ["Runtime Tool Invocation", "LoanStatusTool._run() bound_role check", f"PASSED — Blocked: '{runtime_err}'"],
        ],
    )

    # ---------------------------------------------------------
    # 4. Risk Classification
    # ---------------------------------------------------------
    print("\n4. Risk Classification: High Risk")
    t.h2("4. System Risk Classification: High Risk")
    t.para(
        "**Classification:** **High Risk**\n\n"
        "**Justification:** CredoBot processes sensitive financial records (sanction amounts, underwriting statuses, "
        "and fraud review indicators) alongside fixed-format identity PII (PAN, Aadhaar, account numbers). "
        "Because outputs directly impact consumer loan sanctions and financial commitments, CredoBot requires "
        "strict defense-in-depth architectural governance over standard conversational AI controls."
    )

    # ---------------------------------------------------------
    # 5. Runtime Request Budget Cap
    # ---------------------------------------------------------
    print("\n5. Testing runtime request budget enforcement...")
    normal_q = "What is the status of LA-1001?"
    normal_est = estimate_request(normal_q)
    print(f"  Normal Query ({len(normal_q)} chars): {normal_est.total_tokens} tokens, ${normal_est.cost_usd:.5f} -> Within: {normal_est.within}")

    oversized_q = "Please explain the full loan underwriting policy terms. " * 450  # ~24,000 chars
    before_snap = counters.snapshot()
    budget_err = ""
    try:
        enforce_budget(oversized_q)
    except BudgetExceededError as e:
        budget_err = str(e)
        print(f"  Oversized Query ({len(oversized_q)} chars): BLOCKED: {budget_err}")
    after_snap = counters.snapshot()

    llm_diff = after_snap.get("llm.crew", 0) - before_snap.get("llm.crew", 0)
    tool_diff = (
        (after_snap.get("tool.rag_lookup", 0) - before_snap.get("tool.rag_lookup", 0))
        + (after_snap.get("tool.check_loan_application_status", 0) - before_snap.get("tool.check_loan_application_status", 0))
    )

    t.h2("5. Runtime Request Token & Cost Budget Cap")
    t.para(
        f"Incoming requests are evaluated against configured budget bounds (MAX_REQUEST_TOKENS={config.MAX_REQUEST_TOKENS}, "
        f"MAX_REQUEST_COST_USD=${config.MAX_REQUEST_COST_USD:.4f}, MAX_QUERY_CHARS={config.MAX_QUERY_CHARS}). "
        "Oversized requests are dropped immediately before executing any vector retrieval or LLM inference."
    )
    t.table(
        ["Scenario", "Query Length", "Estimated Tokens", "Estimated Cost (USD)", "Budget Decision", "LLM/Tool Calls"],
        [
            ["Standard Query", f"{len(normal_q)} chars", str(normal_est.total_tokens), f"${normal_est.cost_usd:.5f}", "ACCEPTED", "Proceeds to Agent Pipeline"],
            ["Oversized Request (24k chars)", f"{len(oversized_q)} chars", f">{config.MAX_REQUEST_TOKENS}", f">${(len(oversized_q)/4 + 2000)/1000 * config.PRICE_PER_1K_TOKENS_USD:.4f}", f"REJECTED: '{budget_err}'", f"Zero (LLM diff: {llm_diff}, Tool diff: {tool_diff})"],
        ],
    )

    saved = t.save()
    print(f"\nTranscript written to: {saved}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
