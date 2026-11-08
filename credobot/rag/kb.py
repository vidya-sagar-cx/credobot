"""Knowledge base loader and sentence splitter."""
from dataclasses import dataclass
from pathlib import Path
import re
from credobot import config


@dataclass(frozen=True)
class KBDoc:
    doc_id: str
    text: str
    path: Path


REQUIRED_TOPICS: dict[str, str] = {
    "loan eligibility criteria by loan type": "loan_eligibility",
    "EMI calculation rules": "emi_calculation",
    "credit-card fee structure": "credit_card_fees",
    "KYC document requirements": "kyc_documents",
    "fraud-dispute resolution process": "fraud_dispute",
    "account-closure process": "account_closure",
    "interest-rate slabs": "interest_rate_slabs",
    "prepayment-penalty rules": "prepayment_penalty",
    "minimum-balance requirements": "minimum_balance",
    "credit-score impact factors": "credit_score_factors",
    "joint-account rules": "joint_accounts",
    "NRI-account eligibility": "nri_accounts",
}


def load_kb(kb_dir: Path | None = None) -> list[KBDoc]:
    """Read every *.md in kb_dir (sorted by name), strip, utf-8."""
    target_dir = kb_dir or config.KB_DIR
    docs: list[KBDoc] = []
    for file_path in sorted(target_dir.glob("*.md")):
        doc_id = file_path.stem
        text = file_path.read_text(encoding="utf-8").strip()
        if text:
            docs.append(KBDoc(doc_id=doc_id, text=text, path=file_path))
    return docs


def split_sentences(text: str) -> list[str]:
    """Regex sentence splitter shared across chunking, generation, and guardrails."""
    text = text.strip()
    if not text:
        return []
    parts = re.split(r'(?<=[.!?])\s+(?=[A-Z₹0-9"(])', text)
    return [p.strip() for p in parts if p.strip()]

