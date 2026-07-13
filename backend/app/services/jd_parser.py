"""Job-description parsing: text → structured requirements."""

from app.schemas import ParsedJob
from app.services.llm import llm_available, parse_structured

SYSTEM = """\
You are a job-description parser. Extract the role's requirements into the
given JSON schema. Distinguish hard requirements (required_skills,
min_years_experience, education_required, certifications_required) from
nice-to-haves (preferred_skills). Normalize skill names to their common
industry form. Extract only what is stated — do not invent requirements."""


def parse_job_text(description: str, title: str = "") -> ParsedJob:
    if not llm_available():
        from app.services.heuristics import heuristic_parse_job

        return heuristic_parse_job(description, title)
    content = f"<job_title>{title}</job_title>\n<job_description>\n{description}\n</job_description>"
    return parse_structured(SYSTEM, content, ParsedJob)
