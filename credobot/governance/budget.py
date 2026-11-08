"""Runtime per-request token and cost budget enforcement."""
import math
from dataclasses import dataclass
from credobot import config, counters


class BudgetExceededError(Exception):
    """Raised when an incoming request exceeds runtime token, cost, or character limits."""

    def __init__(self, estimate: "BudgetEstimate", message: str | None = None):
        self.estimate = estimate
        msg = message or (
            f"Request budget exceeded: estimated {estimate.total_tokens} tokens "
            f"(limit: {estimate.limit_tokens}) or estimated ${estimate.cost_usd:.5f} "
            f"(limit: ${estimate.limit_cost_usd:.4f})."
        )
        super().__init__(msg)


@dataclass
class BudgetEstimate:
    query_chars: int
    input_tokens: int
    context_tokens: int
    output_tokens: int
    total_tokens: int
    cost_usd: float
    limit_tokens: int
    limit_cost_usd: float
    limit_chars: int

    @property
    def within(self) -> bool:
        return (
            self.query_chars <= self.limit_chars
            and self.total_tokens <= self.limit_tokens
            and self.cost_usd <= self.limit_cost_usd
        )


def estimate_tokens(text: str) -> int:
    """Heuristic token estimation: ceil(len(text) / 4) without external tokenizers."""
    if not text:
        return 0
    return math.ceil(len(text) / 4)


def estimate_request(query: str) -> BudgetEstimate:
    """Estimate worst-case token consumption and nominal dollar cost for an incoming request.

    Components:
    - input_tokens: query tokens + fixed system prompt overhead across 5 agents
      (3 CrewAI agents + 2 AutoGen review agents).
    - context_tokens: top_k chunks retrieved at fixed chunk size.
    - output_tokens: maximum response generation length.
    """
    q_tokens = estimate_tokens(query)
    overhead = config.PROMPT_OVERHEAD_TOKENS * 5
    input_tok = q_tokens + overhead

    # Context: 3 retrieved chunks at 200 chars (~50 tokens each)
    ctx_tok = config.TOP_K * 50
    out_tok = config.MAX_OUTPUT_TOKENS

    total_tok = input_tok + ctx_tok + out_tok
    cost = (total_tok / 1000.0) * config.PRICE_PER_1K_TOKENS_USD

    return BudgetEstimate(
        query_chars=len(query),
        input_tokens=input_tok,
        context_tokens=ctx_tok,
        output_tokens=out_tok,
        total_tokens=total_tok,
        cost_usd=round(cost, 6),
        limit_tokens=config.MAX_REQUEST_TOKENS,
        limit_cost_usd=config.MAX_REQUEST_COST_USD,
        limit_chars=config.MAX_QUERY_CHARS,
    )


def enforce_budget(query: str) -> BudgetEstimate:
    """Enforce budget limits before invoking LLM or tool calls.

    Raises BudgetExceededError if query exceeds token, cost, or character bounds.
    """
    est = estimate_request(query)
    if not est.within:
        counters.incr("governance.budget_exceeded")
        if est.query_chars > est.limit_chars:
            raise BudgetExceededError(
                est,
                f"Request character length {est.query_chars} exceeds limit {est.limit_chars}.",
            )
        raise BudgetExceededError(est)
    return est
