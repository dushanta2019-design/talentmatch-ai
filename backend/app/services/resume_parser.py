"""Resume parsing: file → text → redaction → structured extraction."""

import io

from app.schemas import ParsedResume
from app.services import pii
from app.services.llm import llm_available, parse_structured

SYSTEM = """\
You are a resume parser. Extract the candidate's job-relevant profile from
the resume text into the given JSON schema. Normalize skill names to their
common industry form (e.g. "ReactJS" -> "React"). Estimate
total_years_experience from the work history when not stated explicitly.
Extract only what is present — do not invent facts."""


def extract_text(data: bytes, mime_type: str, file_name: str = "") -> str:
    """Extract plain text from PDF, DOCX, or plain-text uploads."""
    name = file_name.lower()
    if mime_type == "application/pdf" or name.endswith(".pdf"):
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(data))
        # Text only — embedded images (photos) are intentionally never processed.
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    if name.endswith(".docx") or "wordprocessingml" in mime_type:
        import docx

        document = docx.Document(io.BytesIO(data))
        return "\n".join(p.text for p in document.paragraphs)
    return data.decode("utf-8", errors="ignore")


def parse_resume_text(raw_text: str) -> tuple[str, ParsedResume]:
    """Redact first, then run structured extraction on the redacted text."""
    redacted = pii.redact(raw_text)
    if not llm_available():
        from app.services.heuristics import heuristic_parse_resume

        return redacted, heuristic_parse_resume(redacted)
    parsed = parse_structured(
        SYSTEM,
        f"<resume>\n{redacted}\n</resume>",
        ParsedResume,
    )
    return redacted, parsed
