"""Heuristic (non-LLM) parsers and explanations.

Used when no ANTHROPIC_API_KEY is configured (dev/demo mode) so the full
pipeline — parse → embed → score → explain — still works end-to-end.
Quality is intentionally basic; production uses Claude structured extraction.
"""

import re

from app.schemas import Education, MatchExplanation, ParsedJob, ParsedResume, WorkExperience
from app.services.matching import ScoreBreakdown

# Common tech + business skills to scan for (lowercase).
KNOWN_SKILLS = [
    "python", "java", "javascript", "typescript", "c++", "c#", "go", "rust",
    "ruby", "php", "sql", "html", "css", "react", "angular", "vue", "next.js",
    "node.js", "django", "flask", "fastapi", "spring", ".net", "express",
    "postgresql", "mysql", "mongodb", "redis", "elasticsearch", "sqlite",
    "aws", "azure", "gcp", "docker", "kubernetes", "terraform", "jenkins",
    "git", "linux", "ci/cd", "graphql", "rest", "grpc", "kafka", "spark",
    "hadoop", "airflow", "pandas", "numpy", "scikit-learn", "pytorch",
    "tensorflow", "machine learning", "deep learning", "nlp", "data analysis",
    "excel", "power bi", "tableau", "figma", "photoshop", "illustrator",
    "agile", "scrum", "jira", "project management", "communication",
    "leadership", "salesforce", "seo", "marketing", "accounting",
]

_YEARS_RE = re.compile(r"(\d{1,2})\s*\+?\s*years?", re.I)
_DEGREE_RE = re.compile(
    r"\b(ph\.?d|doctorate|master(?:'s)?|mba|bachelor(?:'s)?|b\.?sc|m\.?sc|"
    r"b\.?tech|m\.?tech|b\.?e|associate|diploma)\b", re.I,
)
_CERT_RE = re.compile(r"^.*\bcertif\w*\b.*$", re.I | re.M)
_TITLE_LINE_RE = re.compile(
    r"^\s*(senior|junior|lead|principal|staff)?\s*[\w /+#.-]{3,60}"
    r"(engineer|developer|manager|analyst|designer|scientist|architect|consultant)\b.*$",
    re.I | re.M,
)


def _find_skills(text: str) -> list[str]:
    low = text.lower()
    found = []
    for skill in KNOWN_SKILLS:
        if re.search(rf"(?<![\w+#]){re.escape(skill)}(?![\w+#])", low):
            found.append(skill.title() if skill.islower() and len(skill) > 3 else skill)
    return found


def _find_years(text: str) -> float | None:
    hits = [int(m.group(1)) for m in _YEARS_RE.finditer(text) if int(m.group(1)) <= 45]
    return float(max(hits)) if hits else None


def _find_education(text: str) -> list[Education]:
    seen, out = set(), []
    for m in _DEGREE_RE.finditer(text):
        deg = m.group(1).lower().rstrip("'s").replace(".", "")
        canon = {"bsc": "Bachelor of Science", "btech": "Bachelor of Technology",
                 "be": "Bachelor of Engineering", "msc": "Master of Science",
                 "mtech": "Master of Technology", "phd": "PhD",
                 "master": "Master's degree", "bachelor": "Bachelor's degree",
                 "mba": "MBA", "doctorate": "Doctorate",
                 "associate": "Associate degree", "diploma": "Diploma"}.get(deg, m.group(1))
        if canon not in seen:
            seen.add(canon)
            out.append(Education(degree=canon))
    return out


def heuristic_parse_resume(text: str) -> ParsedResume:
    titles = _TITLE_LINE_RE.findall(text)
    return ParsedResume(
        summary=text.strip().splitlines()[0][:200] if text.strip() else "",
        skills=_find_skills(text),
        total_years_experience=_find_years(text),
        work_experience=[
            WorkExperience(title=" ".join(t).strip() if isinstance(t, tuple) else str(t))
            for t in titles[:5]
        ],
        education=_find_education(text),
        certifications=[c.strip()[:120] for c in _CERT_RE.findall(text)[:5]],
    )


def heuristic_parse_job(description: str, title: str = "") -> ParsedJob:
    skills = _find_skills(description)
    # Split required vs preferred by section keywords when present.
    low = description.lower()
    preferred_start = min(
        (low.find(k) for k in ("preferred", "nice to have", "bonus") if k in low),
        default=-1,
    )
    if preferred_start > 0:
        required = _find_skills(description[:preferred_start])
        preferred = [s for s in _find_skills(description[preferred_start:]) if s not in required]
    else:
        required, preferred = skills, []
    return ParsedJob(
        title=title,
        summary=description.strip().splitlines()[0][:200] if description.strip() else "",
        required_skills=required,
        preferred_skills=preferred,
        min_years_experience=_find_years(description),
        education_required=(
            _find_education(description)[0].degree if _find_education(description) else None
        ),
    )


def heuristic_explanation(
    resume: ParsedResume, job: ParsedJob, scores: ScoreBreakdown
) -> MatchExplanation:
    strengths = []
    if scores.matched_skills:
        strengths.append(
            f"Candidate evidences {len(scores.matched_skills)} of the listed skills: "
            f"{', '.join(scores.matched_skills[:8])}."
        )
    if (
        resume.total_years_experience is not None
        and job.min_years_experience is not None
        and resume.total_years_experience >= job.min_years_experience
    ):
        strengths.append(
            f"Meets the experience bar ({resume.total_years_experience:g} vs "
            f"{job.min_years_experience:g}+ years required)."
        )
    concerns = []
    if scores.missing_skills:
        concerns.append(
            f"No evidence of required skill(s): {', '.join(scores.missing_skills[:8])}."
        )
    return MatchExplanation(
        strengths=strengths,
        concerns=concerns,
        experience_gaps=scores.gaps.get("experience", []),
        education_certification_gaps=scores.gaps.get("education_certifications", []),
        role_fit_summary=(
            f"Rule-based summary (no LLM configured): overall fit {scores.overall:.0f}/100 "
            f"with {scores.confidence} confidence, driven by skills {scores.skills:.0f} "
            f"and experience {scores.experience:.0f}."
        ),
    )
