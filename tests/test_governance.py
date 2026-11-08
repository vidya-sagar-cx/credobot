"""Unit and integration tests for AI governance: tool ACL, least autonomy, risk, and budget."""
import pytest
from pydantic import BaseModel
from crewai.tools import BaseTool

from credobot import config, counters
from credobot.crew.agents import (
    COMPOSER_ROLE,
    LOOKUP_ROLE,
    RETRIEVAL_ROLE,
    build_agents,
)
from credobot.crew.crew import build_crew
from credobot.governance.budget import (
    BudgetEstimate,
    BudgetExceededError,
    enforce_budget,
    estimate_request,
)
from credobot.governance.tool_policy import (
    TOOL_ACL,
    ToolPermissionError,
    assert_least_autonomy,
    check_tool_assignment,
    make_agent,
)
from credobot.tools.crew_tools import LoanStatusTool, RagLookupTool


def test_only_lookup_agent_has_status_tool():
    agents = build_agents()
    lookup_agent = agents[LOOKUP_ROLE]
    tool_names = [t.name for t in lookup_agent.tools]
    assert "check_loan_application_status" in tool_names

    retrieval_agent = agents[RETRIEVAL_ROLE]
    retrieval_tools = [t.name for t in retrieval_agent.tools]
    assert "check_loan_application_status" not in retrieval_tools

    composer_agent = agents[COMPOSER_ROLE]
    assert len(composer_agent.tools) == 0


def test_wiring_status_tool_to_composer_blocked():
    with pytest.raises(ToolPermissionError) as exc_info:
        make_agent(role=COMPOSER_ROLE, tools=[LoanStatusTool()])
    assert "not permitted to use tool" in str(exc_info.value)


def test_wiring_status_tool_to_retrieval_blocked():
    with pytest.raises(ToolPermissionError) as exc_info:
        make_agent(role=RETRIEVAL_ROLE, tools=[LoanStatusTool()])
    assert "not permitted to use tool" in str(exc_info.value)


def test_unknown_tool_denied_by_default():
    class DummyTool(BaseTool):
        name: str = "unregistered_custom_tool"
        description: str = "A tool not declared in TOOL_ACL."
        def _run(self) -> str:
            return "done"

    with pytest.raises(ToolPermissionError) as exc_info:
        make_agent(role=LOOKUP_ROLE, tools=[DummyTool()])
    assert "denied by default" in str(exc_info.value)


def test_assert_least_autonomy_detects_smuggled_tool():
    crew = build_crew("Check status")
    composer = [a for a in crew.agents if a.role == COMPOSER_ROLE][0]
    smuggled = LoanStatusTool()
    smuggled.bound_role = COMPOSER_ROLE
    composer.tools.append(smuggled)

    with pytest.raises(ToolPermissionError) as exc_info:
        assert_least_autonomy(crew)
    assert "not permitted to use tool" in str(exc_info.value)


def test_runtime_bound_role_check():
    tool = LoanStatusTool()
    tool.bound_role = "Response Composer"
    with pytest.raises(ToolPermissionError) as exc_info:
        tool._run("LA-1001")
    assert "Runtime caller violation" in str(exc_info.value)


def test_delegation_disabled():
    agents = build_agents()
    for role, agent in agents.items():
        assert agent.allow_delegation is False, f"Agent {role} must have allow_delegation=False"


def test_budget_normal_query_within():
    normal_q = "What is the penalty for prepayment of loan LA-1001?"
    est = estimate_request(normal_q)
    assert isinstance(est, BudgetEstimate)
    assert est.within is True
    assert est.total_tokens < config.MAX_REQUEST_TOKENS
    assert est.cost_usd < config.MAX_REQUEST_COST_USD

    # enforce_budget returns estimate on success
    validated_est = enforce_budget(normal_q)
    assert validated_est == est


def test_budget_oversized_rejected():
    oversized_q = "Please explain the full policy. " * 500  # ~16,000 chars
    assert len(oversized_q) > config.MAX_QUERY_CHARS

    with pytest.raises(BudgetExceededError) as exc_info:
        enforce_budget(oversized_q)
    assert exc_info.value.estimate.within is False
    assert exc_info.value.estimate.query_chars > config.MAX_QUERY_CHARS


def test_budget_rejection_before_llm():
    counters.reset()
    before = counters.snapshot()
    oversized_q = "Oversized prompt content. " * 600

    def simulated_run(q: str):
        enforce_budget(q)
        # If budget passes, would call LLM:
        counters.incr("llm.crew")

    with pytest.raises(BudgetExceededError):
        simulated_run(oversized_q)

    after = counters.snapshot()
    # LLM counter was never incremented
    assert after.get("llm.crew", 0) == before.get("llm.crew", 0)
    assert after.get("governance.budget_exceeded", 0) == 1


def test_risk_doc_states_high():
    risk_file = config.ROOT / "credobot" / "governance" / "risk.md"
    assert risk_file.exists(), f"Risk doc missing at {risk_file}"
    content = risk_file.read_text(encoding="utf-8")
    assert "High Risk" in content
    assert "Four-Layer AI Governance Model" in content
    assert "Least-Autonomy Architecture" in content
