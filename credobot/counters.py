"""Thread-safe named counters used as evidence (LLM calls, Chroma queries, tool calls)."""
import threading
from collections import Counter

_lock = threading.Lock()
_counts: Counter[str] = Counter()


def incr(name: str, n: int = 1) -> None:
    with _lock:
        _counts[name] += n


def get(name: str) -> int:
    with _lock:
        return _counts[name]


def snapshot() -> dict[str, int]:
    with _lock:
        return dict(_counts)


def reset(*names: str) -> None:
    """Reset specified counters, or all counters if no names provided."""
    with _lock:
        if names:
            for name in names:
                _counts.pop(name, None)
        else:
            _counts.clear()

