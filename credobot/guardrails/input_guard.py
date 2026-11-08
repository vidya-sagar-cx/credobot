"""Input-side guardrails: PII masking and prompt injection detection."""
import re
from dataclasses import dataclass, field
from credobot import counters

# Fixed-format PII patterns for banking domain:
# 1. PAN: 5 uppercase letters, 4 digits, 1 uppercase letter (e.g. ABCDE1234F)
# 2. Aadhaar: 12 digits (first digit 2-9), optionally separated by spaces or hyphens
# 3. Bank Account Number: 9 to 18 contiguous digits
#
# Note: Free-text fields like applicant name and income figures have no reliable
# fixed pattern under keyless local processing and are explicitly out of scope.
# Note: Loan application IDs like LA-1001 have only 4 digits and remain untouched.
PAN_RE = re.compile(r"\b[A-Za-z]{5}[0-9]{4}[A-Za-z]\b")
AADHAAR_RE = re.compile(r"\b[2-9][0-9]{3}[ -]?[0-9]{4}[ -]?[0-9]{4}\b")
ACCOUNT_RE = re.compile(r"\b[0-9]{9,18}\b")

MASKS: list[tuple[str, re.Pattern, str]] = [
    ("PAN", PAN_RE, "[PAN_MASKED]"),
    ("AADHAAR", AADHAAR_RE, "[AADHAAR_MASKED]"),
    ("ACCOUNT", ACCOUNT_RE, "[ACCOUNT_MASKED]"),
]


@dataclass
class MaskResult:
    text: str
    found: dict[str, int] = field(default_factory=dict)

    @property
    def fired(self) -> bool:
        return sum(self.found.values()) > 0


def mask_pii(text: str) -> MaskResult:
    """Mask fixed-format PII (PAN, Aadhaar, Account Number) in text."""
    current = text
    found: dict[str, int] = {}
    for pii_type, pattern, placeholder in MASKS:
        matches = list(pattern.finditer(current))
        if matches:
            found[pii_type] = len(matches)
            current = pattern.sub(placeholder, current)
            counters.incr("guardrails.pii_masked", len(matches))
    return MaskResult(text=current, found=found)


INJECTION_PATTERNS: list[str] = [
    r"ignore (all |any )?(previous|prior|above) (instructions|rules|prompts?)",
    r"disregard (the |your )?(system|previous) (prompt|instructions)",
    r"(reveal|show|print|repeat) (me )?(your|the) (system prompt|hidden instructions|instructions)",
    r"\byou are now\b",
    r"\b(dan|developer mode|jailbreak)\b",
    r"act as (an? )?(unrestricted|unfiltered)",
    r"(approve|mark) (my|this|the) (loan application|loan|application)( (as )?(approved|immediately))?",
    r"<\s*/?\s*(system|assistant)\s*>",
]

COMPILED_INJECTIONS: list[re.Pattern] = [
    re.compile(p, re.IGNORECASE) for p in INJECTION_PATTERNS
]

REFUSAL_INJECTION: str = (
    "I can't help with that request. I can answer X Corp loan-policy questions or check an application's status."
)


@dataclass
class InjectionResult:
    detected: bool
    matched: list[str] = field(default_factory=list)


def detect_injection(text: str) -> InjectionResult:
    """Detect prompt injection attempts against compiled heuristic signatures."""
    matched: list[str] = []
    for pattern in COMPILED_INJECTIONS:
        if pattern.search(text):
            matched.append(pattern.pattern)
    detected = len(matched) > 0
    if detected:
        counters.incr("guardrails.injection_blocked")
    return InjectionResult(detected=detected, matched=matched)


@dataclass
class InputCheck:
    masked_text: str
    pii: dict[str, int]
    injection: InjectionResult
    events: list[str]
    blocked: bool


def check_input(text: str) -> InputCheck:
    """Execute input-side guardrails: mask PII first, then scan for injections."""
    m_res = mask_pii(text)
    inj_res = detect_injection(m_res.text)

    events: list[str] = []
    for pii_type in m_res.found:
        events.append(f"pii_masked:{pii_type}")
    if inj_res.detected:
        events.append("injection_blocked")

    return InputCheck(
        masked_text=m_res.text,
        pii=m_res.found,
        injection=inj_res,
        events=events,
        blocked=inj_res.detected,
    )
