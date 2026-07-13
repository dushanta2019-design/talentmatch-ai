"""Matching algorithm tests — deterministic, no LLM or DB required."""

from app.schemas import Education, ParsedJob, ParsedResume, WorkExperience
from app.services.embeddings import cosine_similarity, embed_text
from app.services.matching import compute_match, normalize_skill

STRONG_RESUME = ParsedResume(
    summary="Backend engineer focused on Python microservices",
    skills=["Python", "PostgreSQL", "AWS", "Docker", "Kubernetes", "FastAPI"],
    total_years_experience=7,
    work_experience=[WorkExperience(title="Senior Backend Engineer", company="Acme",
                                    start_year=2018, end_year=None)],
    education=[Education(degree="Bachelor of Science", field="Computer Science")],
    certifications=["AWS Certified Solutions Architect"],
)

WEAK_RESUME = ParsedResume(
    summary="Graphic designer",
    skills=["Photoshop", "Illustrator", "Figma"],
    total_years_experience=2,
    education=[Education(degree="Diploma", field="Design")],
)

JOB = ParsedJob(
    title="Senior Python Engineer",
    required_skills=["Python", "PostgreSQL", "AWS"],
    preferred_skills=["Kubernetes", "FastAPI"],
    min_years_experience=5,
    education_required="Bachelor's degree",
    certifications_required=["AWS Certified Solutions Architect"],
)


def _score(resume: ParsedResume) -> float:
    r_emb = embed_text(" ".join(resume.skills) + " " + resume.summary)
    j_emb = embed_text(" ".join(JOB.required_skills) + " " + JOB.title)
    return compute_match(resume, JOB, r_emb, j_emb)


def test_scores_within_bounds():
    for resume in (STRONG_RESUME, WEAK_RESUME):
        result = _score(resume)
        assert 0.0 <= result.overall <= 100.0


def test_strong_candidate_outranks_weak():
    assert _score(STRONG_RESUME).overall > _score(WEAK_RESUME).overall + 15


def test_strong_candidate_has_full_skill_coverage():
    result = _score(STRONG_RESUME)
    assert result.missing_skills == []
    assert result.skills == 100.0
    assert result.experience == 100.0


def test_weak_candidate_reports_gaps():
    result = _score(WEAK_RESUME)
    assert set(result.missing_skills) == {"Python", "PostgreSQL", "AWS"}
    assert result.gaps["experience"]  # under required years
    assert result.gaps["role_fit"]


def test_confidence_reflects_evidence():
    assert _score(STRONG_RESUME).confidence == "high"
    empty = ParsedResume()
    sparse_job = ParsedJob(title="X")
    assert compute_match(empty, sparse_job, None, None).confidence == "low"


def test_skill_alias_matching():
    assert normalize_skill("ReactJS") == normalize_skill("react")
    assert normalize_skill("k8s") == "kubernetes"
    assert normalize_skill("AWS") == "amazon web services"


def test_no_skills_in_jd_is_neutral():
    job = ParsedJob(title="Generalist")
    result = compute_match(STRONG_RESUME, job, None, None)
    assert result.skills == 50.0


def test_cosine_similarity_of_identical_texts_is_one():
    v = embed_text("python backend engineer")
    assert abs(cosine_similarity(v, v) - 1.0) < 1e-9


def test_embeddings_are_deterministic():
    assert embed_text("hello world") == embed_text("hello world")
