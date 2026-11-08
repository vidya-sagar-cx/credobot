# Plan 02 — Knowledge base

## Goal
13 original, fabricated X Corp policy documents in `kb/` (one per required topic plus one
on the loan-application process), each 3–5 sentences, written so retrieval can
discriminate between topics. Plus a tiny loader and a coverage test.

## Brief tasks
T2. Acceptance: "knowledge base has ≥12 documents covering every required topic".

## Depends on
00

## Read first
`docs/BRIEF.md` "Required knowledge-base topics".

## Files
```
+ kb/<doc_id>.md   × 13
+ credobot/rag/kb.py
+ tests/test_kb.py
```

## Documents (doc_id = filename stem)
| doc_id | Required topic | Must mention (to support eval key points later) |
|---|---|---|
| `loan_eligibility` | loan eligibility criteria by loan type | age bands, minimum income, credit score floor per loan type (Personal/Home/Auto/Education/Business), employment/business vintage |
| `emi_calculation` | EMI calculation rules | reducing-balance formula `EMI = P·r·(1+r)^n / ((1+r)^n − 1)`, r = annual rate/12, rounding to nearest rupee, first-EMI date rule |
| `credit_card_fees` | credit-card fee structure | joining/annual fee + waiver spend, late-payment fee slabs, cash-advance fee %, forex markup % |
| `kyc_documents` | KYC document requirements | PAN mandatory, Aadhaar/passport/voter ID/driving licence as OVD, address proof, re-KYC periodicity |
| `fraud_dispute` | fraud-dispute resolution process | report within 3 working days for zero liability, card block, provisional credit in 10 days, resolution within 90 days |
| `account_closure` | account-closure process | written/online request, zero balance & no pending dues, closure charge if closed within 1 year, cheque-book return |
| `interest_rate_slabs` | interest-rate slabs | rate ranges by loan type and by credit-score band (e.g. 750+, 700–749, <700) |
| `prepayment_penalty` | prepayment-penalty rules | floating-rate individual loans: nil penalty; fixed-rate: % of prepaid principal; lock-in months; business loans different |
| `minimum_balance` | minimum-balance requirements | metro/urban/rural average monthly balance amounts, non-maintenance charges, BSBD exemption |
| `credit_score_factors` | credit-score impact factors | payment history, utilisation (<30%), credit age, hard enquiries, mix |
| `joint_accounts` | joint-account rules | max holders, operating modes (either-or-survivor, jointly), nomination, minor accounts |
| `nri_accounts` | NRI-account eligibility | NRE/NRO/FCNR, who qualifies (FEMA residency), repatriability, tax treatment of interest |
| `loan_application_process` | (extra) application lifecycle | meaning of Submitted/Under Review/Approved/Rejected/Disbursed, typical turnaround days, fraud-review hold, escalation to lending ops |

Writing rules:
- 3–5 sentences each (the brief allows 2–5; use ≥3 so sentence chunking has material).
- Own words; fictional "X Corp Bank" numbers; INR amounts written like `₹10,000`.
- Each doc must contain distinctive vocabulary for its topic (e.g. "EMI", "PAN",
  "NRE") so a short query retrieves it; avoid two docs sharing the same lead sentence.
- Plain text, no markdown headings inside (first line is the first sentence), UTF-8, LF.
- Sentences end with `.`; avoid abbreviations with periods (write "for example" not
  "e.g.") so the regex sentence splitter in plan 03 stays accurate.

## Code changes — `credobot/rag/kb.py`
```python
from credobot import config
@dataclass(frozen=True)
class KBDoc:
    doc_id: str
    text: str
    path: Path

REQUIRED_TOPICS: dict[str, str] = {   # topic label from brief → doc_id
    "loan eligibility criteria by loan type": "loan_eligibility",
    ...  # all 12
}

def load_kb(kb_dir: Path | None = None) -> list[KBDoc]:
    """Read every *.md in kb_dir (sorted by name), strip, utf-8."""
def split_sentences(text: str) -> list[str]:
    """Regex splitter: re.split(r'(?<=[.!?])\s+(?=[A-Z₹0-9"(])', text.strip()).
    Shared by plan 03 (sentence chunking), 04 (extractive answers), 09 (support check)."""
```

## Tests — `tests/test_kb.py`
- `test_at_least_12_docs` — `len(load_kb()) >= 12`.
- `test_every_required_topic_has_doc` — every `REQUIRED_TOPICS` value exists in `kb/`.
- `test_sentence_counts` — each doc has 2–5 sentences via `split_sentences` (target 3–5).
- `test_utf8_and_nonempty` — every file decodes as UTF-8 and is non-empty.
- `test_split_sentences_basic` — `"A b. C d! E f?"` → 3 sentences; `"₹10,000 fee. Next."` → 2.

## Steps
- [x] Write the 13 kb files
- [x] Implement `credobot/rag/kb.py`
- [x] Write tests; run Verify
- [x] Record `kb_doc_ids`; update PROGRESS; commit

## Verify
1. `uv run pytest tests/test_kb.py -q` → pass.
2. `uv run python -c "from credobot.rag.kb import load_kb, split_sentences as s; [print(d.doc_id, len(s(d.text))) for d in load_kb()]"`
   → 13 lines, every count 3–5.

## Record in DECISIONS.md
`kb_doc_ids` (all 13).

## Pitfalls
- Policy numbers are fabricated; don't copy real bank text.
- Don't put the brief's PII examples in the KB.

## Commit
`plan 02: knowledge base (13 policy documents) and loader`
