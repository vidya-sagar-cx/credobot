"""Application-layer least-autonomy tool access control policy and agent constructor."""
from typing import Any
from crewai import Agent, Crew

TOOL_ACL: dict[str, frozenset[str]] = {
    "check_loan_application_status": frozenset({"Lookup Agent"}),
    "rag_lookup": frozenset({"Retrieval Agent"}),
}


class ToolPermissionError(PermissionError):
    """Raised when an agent attempts to hold or execute a tool outside its least-autonomy grant."""
    pass


def check_tool_assignment(role: str, tools: list[Any]) -> None:
    """Enforce deny-by-default tool assignment based on declared TOOL_ACL."""
    for tool in tools:
        name = getattr(tool, "name", str(tool))
        if name not in TOOL_ACL:
            raise ToolPermissionError(
                f"Tool '{name}' is not registered in TOOL_ACL and is denied by default."
            )
        allowed = TOOL_ACL[name]
        if role not in allowed:
            raise ToolPermissionError(
                f"Role '{role}' is not permitted to use tool '{name}'. "
                f"Allowed roles: {sorted(list(allowed))}."
            )


def make_agent(*, role: str, tools: list[Any], **kwargs: Any) -> Agent:
    """Construct an Agent enforcing least autonomy and binding role to tools."""
    check_tool_assignment(role, tools)
    # Bind owning role to each tool instance for runtime enforcement
    for tool in tools:
        try:
            tool.bound_role = role
        except Exception:
            object.__setattr__(tool, "bound_role", role)
    return Agent(role=role, tools=tools, **kwargs)


def assert_least_autonomy(crew: Crew) -> None:
    """Defence-in-depth verification of all agents in a Crew prior to execution."""
    for agent in crew.agents:
        if getattr(agent, "allow_delegation", False):
            raise ToolPermissionError(
                f"Agent '{agent.role}' has allow_delegation=True. "
                "Delegation must be disabled to prevent indirect tool access."
            )
        tools = getattr(agent, "tools", []) or []
        check_tool_assignment(agent.role, tools)
        for tool in tools:
            bound = getattr(tool, "bound_role", None)
            if bound != agent.role:
                raise ToolPermissionError(
                    f"Tool '{tool.name}' on agent '{agent.role}' has mismatched bound_role '{bound}'."
                )
