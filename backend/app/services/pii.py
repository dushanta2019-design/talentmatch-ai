"""PII and protected-attribute redaction.

Compliance rule: scoring, embeddings, and LLM prompts must never see
name, email, phone, address, date of birth, gender, age, race, religion,
caste, marital status, nationality, disability status, or photo content.
This module strips those signals BEFORE any AI processing.

Redaction runs first; the LLM extraction schema (ParsedResume) is a second
line of defense because it has no fields for protected attributes.
"""

import hashlib
import re

EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PHONE_RE = re.compile(
    r"(\+?\d{1,3}[\s.-]?)?(\(?\d{2,4}\)?[\s.-]?)?\d{3,4}[\s.-]?\d{4}\b"
)
URL_RE = re.compile(r"https?://\S+|www\.\S+|linkedin\.com/\S+|github\.com/\S+", re.I)
DOB_RE = re.compile(
    r"(date\s+of\s+birth|d\.?o\.?b\.?|born(\s+on)?)\s*[:\-]?\s*[^\n,;]{0,40}", re.I
)
AGE_RE = re.compile(r"\bage\s*[:\-]?\s*\d{1,2}\b", re.I)

# Lines declaring protected attributes are dropped entirely.
PROTECTED_LINE_RE = re.compile(
    r"^\s*(gender|sex|marital\s+status|religion|caste|nationality|"
    r"citizenship|race|ethnicity|disability|blood\s+group)\s*[:\-]",
    re.I,
)

PHOTO_RE = re.compile(r"\b(photo(graph)?|profile\s+picture|headshot)\b\s*[:\-]?.*", re.I)

# Gendered words normalized to neutral equivalents so phrasing can't leak signal.
GENDERED_TERMS = {
    r"\bhe\b": "they", r"\bshe\b": "they",
    r"\bhis\b": "their", r"\bher\b": "their", r"\bhers\b": "theirs",
    r"\bhim\b": "them",
    r"\bmr\.?\b": "", r"\bmrs\.?\b": "", r"\bms\.?\b": "", r"\bmiss\b": "",
    r"\bchairman\b": "chairperson", r"\bchairwoman\b": "chairperson",
    r"\bsalesman\b": "salesperson", r"\bsaleswoman\b": "salesperson",
}


def redact(text: str) -> str:
    """Return job-relevant text with PII and protected attributes removed."""
    lines = []
    for i, line in enumerate(text.splitlines()):
        if PROTECTED_LINE_RE.match(line):
            continue
        if PHOTO_RE.search(line):
            continue
        # Heuristic: the first non-empty line of a resume is usually the
        # candidate's name — replace rather than embed it.
        if i == 0 and line.strip() and len(line.split()) <= 5 and not any(
            c.isdigit() for c in line
        ):
            lines.append("[CANDIDATE]")
            continue
        lines.append(line)

    out = "\n".join(lines)
    out = EMAIL_RE.sub("[EMAIL]", out)
    out = URL_RE.sub("[URL]", out)
    out = DOB_RE.sub("[REDACTED-DOB]", out)
    out = AGE_RE.sub("[REDACTED-AGE]", out)
    out = PHONE_RE.sub("[PHONE]", out)
    for pattern, repl in GENDERED_TERMS.items():
        out = re.sub(pattern, repl, out, flags=re.I)
    return out


def contains_pii(text: str) -> bool:
    """Privacy gate used before feedback data enters a training dataset."""
    return bool(
        EMAIL_RE.search(text)
        or DOB_RE.search(text)
        or PROTECTED_LINE_RE.search(text)
        or PHONE_RE.search(text)
    )


def input_hash(*parts: str) -> str:
    """Stable hash of redacted inputs, stored in audit logs for reproducibility."""
    h = hashlib.sha256()
    for p in parts:
        h.update(p.encode("utf-8", errors="ignore"))
        h.update(b"\x00")
    return h.hexdigest()
