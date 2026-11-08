"""Agent definitions for CredoBot CrewAI workflow."""
from typing import Any
from credobot import config  # noqa: F401
from credobot.governance.tool_policy import make_agent
from credobot.llm import factory
from credobot.tools.crew_tools import LoanStatusTool, RagLookupTool
from crewai import Agent

RETRIEVAL_ROLE: str = "Retrieval Agent"
LOOKUP_ROLE: str = "Lookup Agent"
COMPOSER_ROLE: str = "Response Composer"


def build_agents(llm: Any = None) -> dict[str, Agent]:
    """Construct the three standard CrewAI agents with assigned roles and tools."""
    llm = llm or factory.get_crew_llm()

    retrieval = make_agent(
        role=RETRIEVAL_ROLE,
        goal="Retrieve accurate policy information from the X Corp knowledge base.",
        backstory="You are an expert policy researcher with direct access to bank underwriting documentation.",
        tools=[RagLookupTool()],
        llm=llm,
        allow_delegation=False,
        max_iter=3,
        verbose=False,
    )

    lookup = make_agent(
        role=LOOKUP_ROLE,
        goal="Look up loan application records and check their review status and escalation urgency.",
        backstory="You are a lending operations specialist who accesses core banking application databases.",
        tools=[LoanStatusTool()],
        llm=llm,
        allow_delegation=False,
        max_iter=3,
        verbose=False,
    )

    composer = make_agent(
        role=COMPOSER_ROLE,
        goal="Synthesize policy knowledge and loan status records into a coherent, structured response.",
        backstory="You are the lead customer support response composer for X Corp Bank.",
        tools=[],
        llm=llm,
        allow_delegation=False,
        max_iter=3,
        verbose=False,
    )

    return {
        RETRIEVAL_ROLE: retrieval,
        LOOKUP_ROLE: lookup,
        COMPOSER_ROLE: composer,
    }
