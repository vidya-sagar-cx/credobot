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
        if role == "Retrieval Agent":
            return "NO_POLICY_QUESTION"
        return "I don't know — no suitable tool or information available."

    def compose(self, prompt: list[dict[str, str]], response_model: Any = None) -> str:
        """Compose structured response combining retrieval and lookup outputs."""
        import json
        from credobot.crew.schemas import CrewResponse, LoanStatus

        prompt_text = "\n".join(m.get("content", "") for m in prompt)

        # Extract only the task context portion (after 'This is the context you're working with:')
        # to avoid matching OpenAPI schema definitions.
        context_text = prompt_text
        if "This is the context you're working with:" in prompt_text:
            context_text = prompt_text.split("This is the context you're working with:", 1)[1]
        if "Provide your complete response:" in context_text:
            context_text = context_text.split("Provide your complete response:", 1)[0]

        rag_answer = ""
        sources: list[str] = []
        grounded = False
        fallback = True
        top_similarity: float | None = None
        record: LoanStatus | None = None

        blocks = context_text.split("----------")
        for b in blocks:
            b = b.strip()
            if not b or b in ("NO_RECORD_ID", "NO_POLICY_QUESTION"):
                continue
            if "{" in b and "}" in b:
                try:
                    j_str = b[b.find("{") : b.rfind("}") + 1]
                    data = json.loads(j_str)
                    if "top_similarity" in data:
                        rag_answer = data.get("answer", "")
                        sources = data.get("sources", [])
                        grounded = bool(data.get("grounded", False))
                        fallback = bool(data.get("fallback", True))
                        top_similarity = data.get("top_similarity")
                    elif "escalation_score" in data:
                        if "status" in data and "error" not in data:
                            record = LoanStatus(
                                record_id=data["record_id"],
                                category=data["category"],
                                status=data["status"],
                                loan_amount_inr=data["loan_amount_inr"],
                                days_since_created=data["days_since_created"],
                                flagged_for_fraud_review=data["flagged_for_fraud_review"],
                                escalation_score=data["escalation_score"],
                                escalate=data["escalate"],
                            )
                except Exception:
                    pass

        has_record = record is not None
        has_policy = bool(sources) and not fallback

        # If user only asked for application status, ignore extraneous RAG hits
        user_query = react.extract_query(prompt) or ""
        if has_record and react.is_status_only_query(user_query):
            has_policy = False

        # Determine Intent
        if has_record and has_policy:
            intent = "mixed"
        elif has_record:
            intent = "status"
        elif has_policy:
            intent = "policy"
        else:
            intent = "unknown"

        # Construct Answer Text
        status_sentence = ""
        if has_record:
            assert record is not None
            if record.escalate:
                clause = f"Escalation score {record.escalation_score:.2f} — escalated to lending operations."
            else:
                clause = f"Escalation score {record.escalation_score:.2f} — standard processing SLA applies."
            status_sentence = (
                f"Application {record.record_id} ({record.category}, ₹{record.loan_amount_inr:,}) is {record.status}. "
                f"{clause}"
            )

        if has_policy and has_record:
            final_text = f"{rag_answer}\n\n{status_sentence}"
            final_grounded = True
        elif has_policy:
            final_text = rag_answer
            final_grounded = grounded
        elif has_record:
            final_text = status_sentence
            final_grounded = True
        else:
            final_text = (
                rag_answer
                if rag_answer
                else "I don't know — the X Corp policy knowledge base doesn't cover that. Please contact lending operations."
            )
            final_grounded = False

        resp = CrewResponse(
            answer=final_text,
            intent=intent,
            sources=sources if has_policy else [],
            record=record,
            escalate=record.escalate if record else False,
            grounded=final_grounded,
            top_similarity=top_similarity,
            guardrail_events=[],
        )
        return resp.model_dump_json()
