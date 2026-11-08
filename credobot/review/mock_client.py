"""Deterministic content-dependent mock ChatCompletionClient for AutoGen review agents."""
from collections.abc import AsyncGenerator, Sequence
import json
import re
from typing import Any

from autogen_core.models import (
    ChatCompletionClient,
    CreateResult,
    ModelCapabilities,
    ModelInfo,
    RequestUsage,
    UserMessage,
)

from credobot import counters
from credobot.guardrails.output_guard import REFUSAL_UNGROUNDED, sentence_support
from credobot.rag.kb import split_sentences
from credobot.review.schemas import ReviewVerdict


class MockReviewClient(ChatCompletionClient):
    """Deterministic, content-dependent client for the two review agents."""

    def __init__(self, role: str = "reviewer"):
        self.role = role
        self._total_prompt_tokens = 0
        self._total_completion_tokens = 0

    @property
    def model_info(self) -> ModelInfo:
        return ModelInfo(
            vision=False,
            function_calling=False,
            json_output=True,
            family="unknown",
            structured_output=True,
        )

    @property
    def capabilities(self) -> ModelCapabilities:
        return ModelCapabilities(
            vision=False,
            function_calling=False,
            json_output=True,
        )

    def actual_usage(self) -> RequestUsage:
        return RequestUsage(
            prompt_tokens=self._total_prompt_tokens,
            completion_tokens=self._total_completion_tokens,
        )

    def total_usage(self) -> RequestUsage:
        return self.actual_usage()

    def count_tokens(self, messages: Any, **kwargs: Any) -> int:
        total_chars = sum(len(str(getattr(m, "content", ""))) for m in messages)
        return total_chars // 4

    def remaining_tokens(self, messages: Any, **kwargs: Any) -> int:
        return 128_000 - self.count_tokens(messages)

    async def close(self) -> None:
        pass

    async def create(
        self,
        messages: Sequence[Any],
        *,
        tools: Any = (),
        tool_choice: Any = "auto",
        json_output: Any = None,
        extra_create_args: Any = {},
        cancellation_token: Any = None,
    ) -> CreateResult:
        counters.incr("llm.autogen")

        # 1. Parse Task Message from the first UserMessage (Never parse SystemMessage)
        task_text = ""
        for m in messages:
            content = getattr(m, "content", "")
            is_user = (
                isinstance(m, UserMessage)
                or getattr(m, "source", "") == "user"
                or getattr(m, "role", "") == "user"
            )
            if is_user and "<<DRAFT>>" in str(content):
                task_text = str(content)
                break

        # Extract draft
        draft = ""
        if "<<DRAFT>>" in task_text and "<</DRAFT>>" in task_text:
            draft = task_text.split("<<DRAFT>>", 1)[1].split("<</DRAFT>>", 1)[0].strip()

        # Extract context chunks
        context_texts: list[str] = []
        if "<<CONTEXT>>" in task_text and "<</CONTEXT>>" in task_text:
            ctx_raw = task_text.split("<<CONTEXT>>", 1)[1].split("<</CONTEXT>>", 1)[0].strip()
            for line in ctx_raw.splitlines():
                line = line.strip()
                if not line:
                    continue
                clean_line = re.sub(r"^\[\d+\]\s*", "", line)
                if clean_line:
                    context_texts.append(clean_line)

        # Extract optional record dict
        record_dict: dict[str, Any] | None = None
        if "<<RECORD>>" in task_text and "<</RECORD>>" in task_text:
            rec_raw = task_text.split("<<RECORD>>", 1)[1].split("<</RECORD>>", 1)[0].strip()
            try:
                record_dict = json.loads(rec_raw)
            except Exception:
                pass

        # 2. Reviewer Agent Logic
        if self.role == "reviewer":
            sentences = split_sentences(draft)
            unsupported: list[str] = []

            for s in sentences:
                clean_s = s.strip()
                # Check if sentence is verifying an application record
                if record_dict and record_dict.get("record_id", "") in clean_s:
                    # Validate amounts and status against record
                    mismatch = False
                    # Check loan amount mismatch if amounts are mentioned
                    amounts = re.findall(r"₹\s*([0-9,]+)", clean_s)
                    if amounts:
                        amt_int = int(amounts[0].replace(",", ""))
                        if amt_int != record_dict.get("loan_amount_inr"):
                            mismatch = True
                    # Check status mismatch
                    status = record_dict.get("status", "").lower()
                    if status and status not in clean_s.lower():
                        # Status contradicted
                        mismatch = True
                    if mismatch:
                        unsupported.append(clean_s)
                    continue

                # Standard policy groundedness check
                support_items = sentence_support(clean_s, context_texts)
                if not support_items or not all(si.supported for si in support_items):
                    unsupported.append(clean_s)

            if not unsupported:
                resp_content = "REVIEW: PASS\nAll claims in the draft are supported by the provided context."
            else:
                resp_content = "REVIEW: FAIL\nUNSUPPORTED:\n" + "\n".join(f"- {u}" for u in unsupported)

        # 3. Editor Agent Logic
        else:
            # Inspect last reviewer message
            rev_msg = ""
            for m in reversed(messages):
                c = str(getattr(m, "content", ""))
                if c.startswith("REVIEW:"):
                    rev_msg = c
                    break

            if "REVIEW: PASS" in rev_msg:
                verdict = ReviewVerdict(
                    approved=True,
                    final_answer=draft,
                    reason="All claims supported by context.",
                )
            else:
                unsupported_lines: list[str] = []
                if "UNSUPPORTED:" in rev_msg:
                    unsupported_part = rev_msg.split("UNSUPPORTED:", 1)[1]
                    for line in unsupported_part.splitlines():
                        line = line.strip()
                        if line.startswith("- "):
                            unsupported_lines.append(line[2:].strip())

                # Filter sentences: keep supported
                sentences = split_sentences(draft)
                remaining: list[str] = []
                for s in sentences:
                    if s.strip() not in unsupported_lines:
                        remaining.append(s.strip())

                if remaining:
                    revised_answer = " ".join(remaining)
                    reason_msg = (
                        f"Removed {len(unsupported_lines)} unsupported claim(s): "
                        + "; ".join(unsupported_lines)
                    )
                    verdict = ReviewVerdict(
                        approved=False,
                        final_answer=revised_answer,
                        reason=reason_msg,
                    )
                else:
                    verdict = ReviewVerdict(
                        approved=False,
                        final_answer=REFUSAL_UNGROUNDED,
                        reason="All claims in draft were unsupported by context; reverted to refusal.",
                    )

            resp_content = verdict.model_dump_json()

        # Update token accounting
        p_tokens = len(task_text) // 4
        c_tokens = len(resp_content) // 4
        self._total_prompt_tokens += p_tokens
        self._total_completion_tokens += c_tokens

        return CreateResult(
            finish_reason="stop",
            content=resp_content,
            usage=RequestUsage(prompt_tokens=p_tokens, completion_tokens=c_tokens),
            cached=False,
        )

    async def create_stream(
        self,
        messages: Sequence[Any],
        *,
        tools: Any = (),
        tool_choice: Any = "auto",
        json_output: Any = None,
        extra_create_args: Any = {},
        cancellation_token: Any = None,
    ) -> AsyncGenerator[Any, None]:
        res = await self.create(
            messages,
            tools=tools,
            tool_choice=tool_choice,
            json_output=json_output,
            extra_create_args=extra_create_args,
            cancellation_token=cancellation_token,
        )
        yield res
