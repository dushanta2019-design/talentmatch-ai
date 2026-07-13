"""Claude wrapper: structured extraction and explanation with Pydantic-validated JSON.

All prompts receive REDACTED text only (see services/pii.py). The system
prompts additionally instruct the model to ignore any residual personal or
protected-attribute signal.
"""

from typing import TypeVar

import anthropic
from pydantic import BaseModel

from app.config import get_settings

T = TypeVar("T", bound=BaseModel)

FAIRNESS_RULES = """\
Compliance rules (mandatory):
- Base every judgment ONLY on job-relevant evidence: skills, experience,
  education, certifications, and responsibilities.
- NEVER consider or infer name, gender, age, race, religion, caste, marital
  status, photo, nationality, disability, or any other protected attribute.
- If any such information leaks through redaction, ignore it completely and
  do not repeat it in the output.
- Do not make hiring decisions. Produce decision-support analysis only."""


def llm_available() -> bool:
    return bool(get_settings().anthropic_api_key)


def _client() -> anthropic.Anthropic:
    return anthropic.Anthropic(api_key=get_settings().anthropic_api_key)


def parse_structured(system: str, user_content: str, schema: type[T]) -> T:
    """One-shot structured extraction, validated against a Pydantic schema."""
    settings = get_settings()
    response = _client().messages.parse(
        model=settings.llm_model,
        max_tokens=8192,
        system=f"{system}\n\n{FAIRNESS_RULES}",
        messages=[{"role": "user", "content": user_content}],
        output_format=schema,
    )
    if response.parsed_output is None:
        raise ValueError("LLM returned no parseable structured output")
    return response.parsed_output


def model_version() -> str:
    s = get_settings()
    return f"{s.scoring_version}+{s.llm_model}+{s.embedding_provider}:{s.embedding_model}"
