"""MockLLM implementing CrewAI BaseLLM for zero-network deterministic execution."""
from typing import Any
from pydantic import Field
from credobot import config  # noqa: F401
from credobot import counters
from credobot.llm import react
from crewai.llms.base_llm import BaseLLM


class MockLLM(BaseLLM):
    model: str = Field(default="mock-llm")
    llm_type: str = Field(default="mock")

    def __init__(self, model: str = "mock-llm", **kwargs: Any):
        super().__init__(model=model, **kwargs)

    def supports_function_calling(self) -> bool:
        return False

    def supports_stop_words(self) -> bool:
        return True

    def get_context_window_size(self) -> int:
        return 128_000

    def call(
        self,
        messages: Any,
        tools: Any = None,
        callbacks: Any = None,
        available_functions: Any = None,
        from_task: Any = None,
        from_agent: Any = None,
        response_model: Any = None,
    ) -> str:
        """Execute deterministic ReAct step without network or LLM API calls."""
        counters.incr("llm.crew")
        prompt, trace = react.split_prompt_and_trace(messages)
        role = getattr(from_agent, "role", None) or react.role_from_prompt(prompt)
        query = react.extract_query(prompt) or ""
        obs = react.last_observation(trace)

        if role == "Response Composer":
            return react.format_final(self.compose(prompt, response_model))

        if obs is None:
            # Extract tool specifications
            specs: list[react.ToolSpec] = []
            if from_agent and hasattr(from_agent, "tools") and from_agent.tools:
                for t in from_agent.tools:
                    name = getattr(t, "name", "")
                    arg_schema = getattr(t, "args_schema", None)
                    if arg_schema and hasattr(arg_schema, "model_fields"):
                        args = list(arg_schema.model_fields.keys())
                    else:
                        args = []
                    specs.append(react.ToolSpec(name=name, args=args))
            if not specs:
                prompt_text = "\n".join(m["content"] for m in prompt)
                specs = react.parse_tool_specs(prompt_text)

            choice = react.choose_tool_and_args(specs, query, role)
            if choice:
                return react.format_action(*choice)
            return react.format_final(self.no_tool_answer(role, query))

        return react.format_final(obs.strip())

    def no_tool_answer(self, role: str | None, query: str) -> str:
        """Fallback response when no tool can be selected."""
        if role == "Lookup Agent":
            return "NO_RECORD_ID"
        return "I don't know — no suitable tool or information available."

    def compose(self, prompt: list[dict[str, str]], response_model: Any = None) -> str:
        """Compose response; overridden in Plan 08 with full Pydantic schema builder."""
        if response_model is not None:
            try:
                return response_model().model_dump_json()
            except Exception:
                return "{}"
        return "{}"
