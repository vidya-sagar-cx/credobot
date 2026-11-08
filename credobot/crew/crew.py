"""CrewAI orchestration workflow and execution runner."""
from dataclasses import dataclass
from typing import Any
from credobot import config  # noqa: F401
from credobot import counters
from credobot.crew.agents import (
    COMPOSER_ROLE,
    LOOKUP_ROLE,
    RETRIEVAL_ROLE,
    build_agents,
)
from credobot.crew.schemas import CrewResponse, validate_response
from credobot.demos.transcript import Transcript
from crewai import Agent, Crew, Process, Task


def build_tasks(
    query: str, agents: dict[str, Agent], history_note: str = ""
) -> list[Task]:
    """Build the sequential 3-task pipeline for Retrieval, Lookup, and Composer."""
    t_retrieve = Task(
        description=f"Answer the policy part of the question using rag_lookup.\n<<QUERY>>{query}<</QUERY>>",
        expected_output="JSON returned by rag_lookup",
        agent=agents[RETRIEVAL_ROLE],
    )

    t_lookup = Task(
        description=(
            f"If the question mentions a loan application id, look it up; "
            f"otherwise answer NO_RECORD_ID.\n<<QUERY>>{query}<</QUERY>>"
        ),
        expected_output="JSON record or NO_RECORD_ID",
        agent=agents[LOOKUP_ROLE],
    )

    t_compose = Task(
        description=(
            f"<<ROLE:composer>> Combine the retrieval and lookup results into one answer.\n"
            f"<<QUERY>>{query}<</QUERY>>{history_note}"
        ),
        expected_output="CrewResponse JSON",
        agent=agents[COMPOSER_ROLE],
        context=[t_retrieve, t_lookup],
        output_pydantic=CrewResponse,
    )

    return [t_retrieve, t_lookup, t_compose]


def build_crew(query: str, llm: Any = None, history_note: str = "") -> Crew:
    """Construct sequential Crew with three agents."""
    agents = build_agents(llm)
    tasks = build_tasks(query, agents, history_note)
    return Crew(
        agents=list(agents.values()),
        tasks=tasks,
        process=Process.sequential,
        verbose=False,
    )


@dataclass
class CrewRun:
    response: CrewResponse
    retrieval_raw: str
    lookup_raw: str
    tool_calls: dict[str, int]
    llm_calls: int


def run_crew(query: str, history_note: str = "") -> CrewRun:
    """Execute CrewAI multi-agent workflow on a query with tool tracking."""
    before = counters.snapshot()
    crew = build_crew(query, history_note=history_note)
    out = crew.kickoff()

    # Extract individual task outputs
    retrieval_raw = str(crew.tasks[0].output.raw) if crew.tasks[0].output else ""
    lookup_raw = str(crew.tasks[1].output.raw) if crew.tasks[1].output else ""

    # Always validate output against schema
    raw_payload = out.pydantic if getattr(out, "pydantic", None) else out.raw
    validated = validate_response(raw_payload)

    after = counters.snapshot()
    tool_calls = {
        "tool.rag_lookup": after.get("tool.rag_lookup", 0)
        - before.get("tool.rag_lookup", 0),
        "tool.check_loan_application_status": after.get(
            "tool.check_loan_application_status", 0
        )
        - before.get("tool.check_loan_application_status", 0),
    }
    llm_calls = after.get("llm.crew", 0) - before.get("llm.crew", 0)

    return CrewRun(
        response=validated,
        retrieval_raw=retrieval_raw,
        lookup_raw=lookup_raw,
        tool_calls=tool_calls,
        llm_calls=llm_calls,
    )


def main() -> int:
    """Run three demonstration queries: policy-only, status-only, and mixed."""
    demos = [
        ("Policy-only Query", "What documents do I need for KYC?"),
        ("Status-only Query", "What is the status of application LA-1007?"),
        ("Mixed Policy & Status Query", "Can I prepay my loan LA-1001 without penalty?"),
    ]

    print("=" * 70)
    print("CREWAI MULTI-AGENT ORCHESTRATION DEMO")
    print("=" * 70)

    t = Transcript("part2_crew", "Part 2 — CrewAI Multi-Agent Orchestration")
    t.h2("Crew Architecture Overview")
    t.para(
        "A 3-agent sequential CrewAI crew (Retrieval Agent → Lookup Agent → Response Composer) "
        "orchestrates policy RAG retrieval and application record lookup with Pydantic structured output."
    )

    for scenario, query in demos:
        print(f"\nRunning {scenario}: '{query}'...")
        run = run_crew(query)

        print(f"  Retrieval Raw: {run.retrieval_raw[:60]}...")
        print(f"  Lookup Raw:    {run.lookup_raw[:60]}...")
        print(f"  Tool Calls:    {run.tool_calls}")
        print(f"  Intent:        {run.response.intent}")
        print(f"  Answer:        {run.response.answer[:80]}...")
        print(f"  Schema Status: PASS")

        t.h2(f"{scenario}: '{query}'")
        t.para(f"**Intent:** `{run.response.intent}` | **Schema Validation:** `PASS`")
        t.table(
            ["Metric / Step", "Details"],
            [
                ["Query", query],
                ["RAG Tool Calls", str(run.tool_calls.get("tool.rag_lookup", 0))],
                [
                    "Lookup Tool Calls",
                    str(run.tool_calls.get("tool.check_loan_application_status", 0)),
                ],
                ["LLM Steps Executed", str(run.llm_calls)],
                [
                    "Sources Used",
                    ", ".join(run.response.sources)
                    if run.response.sources
                    else "None",
                ],
                [
                    "Application Record",
                    f"{run.response.record.record_id} ({run.response.record.status})"
                    if run.response.record
                    else "None",
                ],
                ["Escalate Flag", str(run.response.escalate)],
            ],
        )
        t.h2(f"Raw Agent Traces — {scenario}")
        t.para("**Retrieval Agent Output:**")
        t.code(run.retrieval_raw, lang="json")
        t.para("**Lookup Agent Output:**")
        t.code(run.lookup_raw, lang="json")
        t.para("**Final Validated CrewResponse JSON:**")
        t.code(run.response.model_dump_json(indent=2), lang="json")

    saved = t.save()
    print(f"\nTranscript written to: {saved}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
