"""Hybrid matching algorithm.

overall = w_semantic * semantic + w_skills * skills
        + w_experience * experience + w_education * education   (each 0..100)

- semantic:   cosine similarity of redacted-resume vs JD embeddings,
              rescaled to 0..100
- skills:     weighted coverage of required (x2) and preferred (x1) skills,
              with fuzzy/alias matching
- experience: candidate years vs required years (partial credit below,
              full credit at/above requirement)
- education:  degree-level satisfaction + required-certification coverage

Confidence reflects how much structured evidence was available, not how
high the score is.
"""

from dataclasses import dataclass, field

from app.config import get_settings
from app.schemas import ParsedJob, ParsedResume
from app.services.embeddings import cosine_similarity

# Common alias groups so "JS" matches "JavaScript" etc.
SKILL_ALIASES: dict[str, set[str]] = {
    "javascript": {"js", "ecmascript"},
    "typescript": {"ts"},
    "python": {"py"},
    "postgresql": {"postgres", "psql"},
    "kubernetes": {"k8s"},
    "amazon web services": {"aws"},
    "google cloud platform": {"gcp", "google cloud"},
    "machine learning": {"ml"},
    "natural language processing": {"nlp"},
    "continuous integration": {"ci/cd", "ci-cd", "cicd"},
    "react": {"reactjs", "react.js"},
    "node.js": {"node", "nodejs"},
}

_CANON: dict[str, str] = {}
for canon, aliases in SKILL_ALIASES.items():
    _CANON[canon] = canon
    for a in aliases:
        _CANON[a] = canon


def normalize_skill(skill: str) -> str:
    s = skill.strip().lower()
    return _CANON.get(s, s)


def _skill_matches(required: str, candidate_skills: set[str]) -> bool:
    r = normalize_skill(required)
    if r in candidate_skills:
        return True
    # substring containment for compound skills ("react" ⊂ "react native")
    return any(r in c or c in r for c in candidate_skills if len(r) > 2 and len(c) > 2)


@dataclass
class ScoreBreakdown:
    overall: float = 0.0
    semantic: float = 0.0
    skills: float = 0.0
    experience: float = 0.0
    education: float = 0.0
    confidence: str = "low"
    matched_skills: list[str] = field(default_factory=list)
    missing_skills: list[str] = field(default_factory=list)
    gaps: dict = field(default_factory=dict)


def _score_skills(resume: ParsedResume, job: ParsedJob) -> tuple[float, list[str], list[str]]:
    cand = {normalize_skill(s) for s in resume.skills}
    # skills mentioned in work-experience highlights count too
    for we in resume.work_experience:
        for h in we.highlights:
            pass  # highlights are free text; embedding score covers them

    matched, missing = [], []
    weighted_hit, weighted_total = 0.0, 0.0

    for s in job.required_skills:
        weighted_total += 2.0
        if _skill_matches(s, cand):
            weighted_hit += 2.0
            matched.append(s)
        else:
            missing.append(s)
    for s in job.preferred_skills:
        weighted_total += 1.0
        if _skill_matches(s, cand):
            weighted_hit += 1.0
            matched.append(s)

    if weighted_total == 0:
        return 50.0, matched, missing  # JD listed no skills — neutral
    return 100.0 * weighted_hit / weighted_total, matched, missing


def _score_experience(resume: ParsedResume, job: ParsedJob) -> tuple[float, str | None]:
    req = job.min_years_experience
    have = resume.total_years_experience
    if req is None:
        return 70.0, None  # nothing required — mildly positive neutral
    if have is None:
        return 40.0, "Years of experience could not be determined from the resume."
    if have >= req:
        return 100.0, None
    ratio = have / req if req else 1.0
    gap = f"Has ~{have:g} years of experience; role asks for {req:g}+."
    return max(10.0, 100.0 * ratio), gap


_DEGREE_RANK = {"phd": 5, "doctorate": 5, "master": 4, "mba": 4, "bachelor": 3,
                "associate": 2, "diploma": 1, "high school": 0}


def _degree_rank(text: str) -> int:
    t = text.lower()
    return max((rank for kw, rank in _DEGREE_RANK.items() if kw in t), default=-1)


def _score_education(resume: ParsedResume, job: ParsedJob) -> tuple[float, list[str]]:
    gaps: list[str] = []
    parts: list[float] = []

    if job.education_required:
        need = _degree_rank(job.education_required)
        have = max((_degree_rank(e.degree) for e in resume.education), default=-1)
        if need <= 0 or have >= need:
            parts.append(100.0)
        elif have >= 0:
            parts.append(60.0)
            gaps.append(
                f"Role asks for {job.education_required}; highest degree found is lower."
            )
        else:
            parts.append(30.0)
            gaps.append("No education matching the requirement was found on the resume.")

    if job.certifications_required:
        cand_certs = {c.lower() for c in resume.certifications}
        hits = sum(
            1 for c in job.certifications_required
            if any(c.lower() in cc or cc in c.lower() for cc in cand_certs)
        )
        parts.append(100.0 * hits / len(job.certifications_required))
        for c in job.certifications_required:
            if not any(c.lower() in cc or cc in c.lower() for cc in cand_certs):
                gaps.append(f"Missing required certification: {c}")

    return (sum(parts) / len(parts) if parts else 70.0), gaps


def _confidence(resume: ParsedResume, job: ParsedJob) -> str:
    evidence = 0
    evidence += 1 if resume.skills else 0
    evidence += 1 if resume.work_experience else 0
    evidence += 1 if resume.total_years_experience is not None else 0
    evidence += 1 if (job.required_skills or job.preferred_skills) else 0
    evidence += 1 if job.min_years_experience is not None else 0
    if evidence >= 4:
        return "high"
    if evidence >= 2:
        return "medium"
    return "low"


def compute_match(
    resume: ParsedResume,
    job: ParsedJob,
    resume_embedding: list[float] | None,
    job_embedding: list[float] | None,
) -> ScoreBreakdown:
    settings = get_settings()

    if resume_embedding and job_embedding:
        sim = cosine_similarity(resume_embedding, job_embedding)
        semantic = max(0.0, min(1.0, (sim + 1) / 2)) * 100.0
    else:
        semantic = 50.0

    skills, matched, missing = _score_skills(resume, job)
    experience, exp_gap = _score_experience(resume, job)
    education, edu_gaps = _score_education(resume, job)

    overall = (
        settings.weight_semantic * semantic
        + settings.weight_skills * skills
        + settings.weight_experience * experience
        + settings.weight_education * education
    )

    gaps: dict = {"experience": [], "education_certifications": edu_gaps, "role_fit": []}
    if exp_gap:
        gaps["experience"].append(exp_gap)
    if missing:
        gaps["role_fit"].append(
            f"{len(missing)} required skill(s) not evidenced: {', '.join(missing[:8])}"
        )

    return ScoreBreakdown(
        overall=round(min(100.0, max(0.0, overall)), 2),
        semantic=round(semantic, 2),
        skills=round(skills, 2),
        experience=round(experience, 2),
        education=round(education, 2),
        confidence=_confidence(resume, job),
        matched_skills=sorted(set(matched)),
        missing_skills=missing,
        gaps=gaps,
    )
