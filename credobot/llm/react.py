"""ReAct prompt parsing and tool dispatch helpers for MockLLM."""
import json
import re
from dataclasses import dataclass, field
from typing import Any
from credobot.tools.loan_status import RECORD_ID_RE

QUERY_RE: re.Pattern = re.compile(r"<<QUERY>>(.*?)<</QUERY>>", re.DOTALL)
ROLE_RE: re.Pattern = re.compile(r"<<ROLE:(.*?)>>", re.IGNORECASE)

TOOL_BLOCK_RE: re.Pattern = re.compile(
    r"Tool Name:\s*(?P<name>[^\n]+)\s*\n"
    r"(?:Tool Description:\s*(?P<desc>[^\n]*)\s*\n)?"
    r"Tool Arguments:\s*(?P<args>\{.*?\})",
    re.DOTALL,
)


@dataclass
class ToolSpec:
    name: str
    args: list[str] = field(default_factory=list)
    description: str = ""


def normalize_messages(messages: Any) -> list[dict[str, str]]:
    """Normalize str or message objects into list of dicts with role and content."""
    if isinstance(messages, str):
        return [{"role": "user", "content": messages}]
    norm: list[dict[str, str]] = []
    for m in messages:
        if isinstance(m, dict):
            role = m.get("role", "user")
            content = m.get("content", "")
        else:
            role = getattr(m, "role", "user")
            content = getattr(m, "content", "") or getattr(m, "text", "")
        norm.append({"role": str(role), "content": str(content)})
    return norm


def split_prompt_and_trace(
    messages: Any,
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    """PITFALL 1 guard: separate the initial prompt/template from subsequent execution trace.

    The 'prompt' contains the system message and first user prompt which contains the template
    'Observation: the result of the action'. The 'trace' contains turns generated after that.
    """
    norm = normalize_messages(messages)
    first_user_idx = -1
    for i, m in enumerate(norm):
        if m["role"] == "user":
            first_user_idx = i
            break
    if first_user_idx == -1:
        return norm, []
    return norm[: first_user_idx + 1], norm[first_user_idx + 1 :]


def last_observation(trace: list[dict[str, str]]) -> str | None:
    """Extract text from the last Observation in the trace, stripping reminders."""
    for m in reversed(trace):
        content = m.get("content", "")
        if "Observation:" in content:
            obs_text = content.split("Observation:", 1)[1].strip()
            # Strip trailing reminder blocks if CrewAI appended any
            for marker in ["\nThought:", "\nRemember", "\nIMPORTANT", "\nAction:"]:
                if marker in obs_text:
                    obs_text = obs_text.split(marker)[0].strip()
            return obs_text
    return None


def extract_query(prompt_msgs: list[dict[str, str]]) -> str | None:
    """Extract embedded query delimited by <<QUERY>>...<</QUERY>>."""
    for m in prompt_msgs:
        match = QUERY_RE.search(m["content"])
        if match:
            return match.group(1).strip()
    return None


def role_from_prompt(prompt_msgs: list[dict[str, str]]) -> str | None:
    """Determine agent role from embedded tag or prompt keywords."""
    for m in prompt_msgs:
        content = m.get("content", "")
        match = ROLE_RE.search(content)
        if match:
            return match.group(1).strip()
        if "Response Composer" in content or "Composer" in content:
            return "Response Composer"
        if "Lookup Agent" in content:
            return "Lookup Agent"
        if "Retrieval Agent" in content:
            return "Retrieval Agent"
    return None


def parse_tool_specs(prompt_text: str) -> list[ToolSpec]:
    """Parse tool specifications and their declared argument schemas from prompt text."""
    specs: list[ToolSpec] = []
    for match in re.finditer(r"Tool Name:\s*([^\n]+)", prompt_text):
        name = match.group(1).strip()
        start_pos = match.end()
        args_idx = prompt_text.find("Tool Arguments:", start_pos)
        if args_idx != -1:
            brace_start = prompt_text.find("{", args_idx)
            if brace_start != -1:
                depth = 0
                brace_end = -1
                for idx in range(brace_start, len(prompt_text)):
                    if prompt_text[idx] == "{":
                        depth += 1
                    elif prompt_text[idx] == "}":
                        depth -= 1
                        if depth == 0:
                            brace_end = idx + 1
                            break
                if brace_end != -1:
                    raw_json = prompt_text[brace_start:brace_end]
                    try:
                        schema = json.loads(raw_json)
                        if "properties" in schema and isinstance(schema["properties"], dict):
                            arg_names = list(schema["properties"].keys())
                        else:
                            arg_names = list(schema.keys())
                    except Exception:
                        arg_names = []
                    specs.append(ToolSpec(name=name, args=arg_names))
    return specs


def choose_tool_and_args(
    specs: list[ToolSpec], query: str, role: str | None = None
) -> tuple[str, dict[str, Any]] | None:
    """PITFALL 2 guard: dispatch strictly on declared argument schema, never tool name.

    - spec with 'record_id' arg -> if query has RECORD_ID_RE match, dispatch {"record_id": id}
    - spec with 'query' arg -> dispatch {"query": query}
    """
    id_match = RECORD_ID_RE.search(query)
    record_id = id_match.group(0).upper() if id_match else None

    # First pass: check for record_id requirement if ID is present
    if record_id:
        for s in specs:
            if "record_id" in s.args:
                return s.name, {"record_id": record_id}

    # Second pass: check for query requirement
    for s in specs:
        if "query" in s.args:
            return s.name, {"query": query}

    return None


def format_action(tool_name: str, args: dict[str, Any]) -> str:
    """Format an assistant ReAct action line."""
    return f"Thought: I should use a tool.\nAction: {tool_name}\nAction Input: {json.dumps(args)}"


def format_final(text: str) -> str:
    """Format an assistant ReAct final answer line."""
    return f"Thought: I now can give a great answer\nFinal Answer: {text}"
