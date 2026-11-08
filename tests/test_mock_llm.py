"""Unit tests for MockLLM, ReAct dispatch, pitfall guards, and minimal Crew kickoff."""
import json
from pathlib import Path
import pytest
from pydantic import BaseModel
from credobot import config, counters
from credobot.llm import factory, react
from credobot.llm.mock_llm import MockLLM
from crewai import Agent, Crew, Task
from crewai.tools import BaseTool


def test_template_observation_ignored():
    """Pitfall 1 regression: CrewAI prompt template contains 'Observation: the result of the action'."""
    import crewai

    en_json_path = Path(crewai.__file__).parent / "translations" / "en.json"
    en_data = json.loads(en_json_path.read_text(encoding="utf-8"))
    template_tools_slice = en_data.get("slices", {}).get("tools", "")

    # Construct prompt with the template in system message
    messages = [
        {"role": "system", "content": f"You are a helpful assistant.\n{template_tools_slice}"},
        {"role": "user", "content": "Tool Name: rag_lookup\nTool Arguments: {\"query\": {\"type\": \"str\"}}\n\n<<QUERY>>How is EMI calculated?<</QUERY>>"},
    ]

    _, trace = react.split_prompt_and_trace(messages)
    assert react.last_observation(trace) is None

    llm = MockLLM()
    response = llm.call(messages)
    assert "Action: rag_lookup" in response
    assert "the result of the action" not in response


def test_observation_after_action_used():
    messages = [
        {"role": "system", "content": "System prompt with Observation: the result of the action"},
        {"role": "user", "content": "Tool Name: rag_lookup\nTool Arguments: {\"query\": {\"type\": \"str\"}}\n\n<<QUERY>>How is EMI calculated?<</QUERY>>"},
        {"role": "assistant", "content": "Thought: I should use a tool.\nAction: rag_lookup\nAction Input: {\"query\": \"How is EMI calculated?\"}"},
        {"role": "user", "content": "\nObservation: EMI uses reducing balance.\n\nThought: Now reply."},
    ]

    _, trace = react.split_prompt_and_trace(messages)
    obs = react.last_observation(trace)
    assert obs == "EMI uses reducing balance."

    llm = MockLLM()
    response = llm.call(messages)
    assert response == "Thought: I now can give a great answer\nFinal Answer: EMI uses reducing balance."


def test_rag_lookup_dispatched_by_schema():
    """Pitfall 2 regression: dispatch on schema, never tool name."""
    specs = [
        react.ToolSpec(name="rag_lookup", args=["query"]),
        react.ToolSpec(name="check_loan_application_status", args=["record_id"]),
    ]

    # Query without record ID -> chooses tool with query schema
    t1, a1 = react.choose_tool_and_args(specs, "Explain loan interest")
    assert t1 == "rag_lookup"
    assert a1 == {"query": "Explain loan interest"}

    # Query with ID when only query schema tool is available -> still passes query
    t2, a2 = react.choose_tool_and_args([specs[0]], "status of LA-1007")
    assert t2 == "rag_lookup"
    assert a2 == {"query": "status of LA-1007"}


def test_tool_named_lookup_with_query_schema():
    """A tool named 'lookup_everything' with query schema gets query; 'rag' with record_id gets record_id."""
    tool_lookup = react.ToolSpec(name="lookup_everything", args=["query"])
    tool_rag = react.ToolSpec(name="rag", args=["record_id"])

    t1, a1 = react.choose_tool_and_args([tool_lookup], "What is KYC?")
    assert t1 == "lookup_everything"
    assert a1 == {"query": "What is KYC?"}

    t2, a2 = react.choose_tool_and_args([tool_rag], "What is status of LA-1007?")
    assert t2 == "rag"
    assert a2 == {"record_id": "LA-1007"}


def test_no_record_id_answer():
    specs = [react.ToolSpec(name="loan_status", args=["record_id"])]
    choice = react.choose_tool_and_args(specs, "What is my interest rate?")
    assert choice is None

    llm = MockLLM()
    ans = llm.no_tool_answer("Lookup Agent", "What is my interest rate?")
    assert ans == "NO_RECORD_ID"


def test_supports_function_calling_false():
    llm = MockLLM()
    assert llm.supports_function_calling() is False
    assert llm.supports_stop_words() is True
    assert llm.get_context_window_size() == 128_000


def test_counter_increments():
    counters.reset("llm.crew")
    assert counters.get("llm.crew") == 0
    llm = MockLLM()
    llm.call("<<QUERY>>hi<</QUERY>>")
    assert counters.get("llm.crew") == 1


def test_factory_mock_default():
    assert config.MOCK_LLM is True
    crew_llm = factory.get_crew_llm()
    assert isinstance(crew_llm, MockLLM)

    text_llm = factory.get_text_llm()
    with pytest.raises(RuntimeError, match="MOCK_LLM=false"):
        text_llm("test prompt")


def test_factory_real_requires_key(monkeypatch):
    monkeypatch.setattr(config, "MOCK_LLM", False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY is required"):
        factory.get_crew_llm()

    with pytest.raises(RuntimeError, match="OPENAI_API_KEY is required"):
        factory.get_text_llm()


class EchoInput(BaseModel):
    query: str


class EchoTool(BaseTool):
    name: str = "echo_tool"
    description: str = "Echo back the query input"
    args_schema: type[BaseModel] = EchoInput

    def _run(self, query: str) -> str:
        return f"ECHOED: {query}"


def test_minimal_crew_kickoff_uses_tool():
    """Verifies the CrewAI ReAct loop end-to-end with MockLLM and zero network."""
    tool = EchoTool()
    agent = Agent(
        role="Retrieval Agent",
        goal="Retrieve info",
        backstory="Expert retrieval agent",
        llm=MockLLM(),
        tools=[tool],
        verbose=False,
    )
    task = Task(
        description="Search info for <<QUERY>>hello world<</QUERY>>",
        expected_output="Final echoed string",
        agent=agent,
    )
    crew = Crew(agents=[agent], tasks=[task], verbose=False)
    result = crew.kickoff()
    assert "ECHOED: hello world" in str(result)
