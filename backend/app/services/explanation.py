"""LLM match-explanation system.

Given structured (already-redacted) profiles plus the deterministic score
breakdown, Claude writes an evidence-based explanation. It never changes
the score — it explains it.
"""

from app.schemas import MatchExplanation, ParsedJob, ParsedResume
from app.services.llm import llm_available, parse_structured
from app.services.matching import ScoreBreakdown

SYSTEM = """\
You are a hiring decision-SUPPORT assistant. You are given a candidate
profile (already anonymized), a job's requirements, and a deterministic
score breakdown. Write an evidence-based explanation of the match.

Rules:
- Cite concrete evidence (skills, roles, years, certifications) for every
  strength and concern. Never speculate about the person.
- Do not recommend hiring or rejecting. Frame everything as points for a
  human reviewer to weigh.
- Keep each bullet to one sentence."""


def explain_match(
    resume: ParsedResume, job: ParsedJob, scores: ScoreBreakdown
) -> MatchExplanation:
    if not llm_available():
        from app.services.heuristics import heuristic_explanation

        return heuristic_explanation(resume, job, scores)
    content = f"""\
<candidate_profile>
{resume.model_dump_json(indent=2)}
</candidate_profile>

<job_requirements>
{job.model_dump_json(indent=2)}
</job_requirements>

<score_breakdown>
overall={scores.overall} semantic={scores.semantic} skills={scores.skills}
experience={scores.experience} education={scores.education}
confidence={scores.confidence}
matched_skills={scores.matched_skills}
missing_skills={scores.missing_skills}
gaps={scores.gaps}
</score_breakdown>

Explain this match for a human reviewer."""
    explanation = parse_structured(SYSTEM, content, MatchExplanation)
    explanation.recommendation_note = (
        "Decision support only — a human reviewer must make the final decision."
    )
    return explanation
