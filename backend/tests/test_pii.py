"""Security & privacy checks: the redaction layer must strip everything the
compliance policy forbids the AI from seeing."""

from app.services.pii import contains_pii, input_hash, redact

SAMPLE = """John A. Smith
Email: john.smith@example.com | Phone: +1 (555) 123-4567
Date of Birth: 12 March 1991
Gender: Male
Marital Status: Married
Nationality: Canadian
Photo: attached headshot.jpg
linkedin.com/in/johnsmith

Senior Python developer. He led a team of 8 engineers building
microservices on AWS with PostgreSQL and Kubernetes.
"""


def test_redacts_email_and_phone():
    out = redact(SAMPLE)
    assert "john.smith@example.com" not in out
    assert "555" not in out


def test_redacts_name_line():
    out = redact(SAMPLE)
    assert "John A. Smith" not in out
    assert "[CANDIDATE]" in out


def test_drops_protected_attribute_lines():
    out = redact(SAMPLE).lower()
    assert "gender" not in out
    assert "marital" not in out
    assert "nationality" not in out
    assert "canadian" not in out


def test_redacts_dob_and_photo():
    out = redact(SAMPLE).lower()
    assert "12 march 1991" not in out
    assert "headshot" not in out


def test_neutralizes_gendered_language():
    out = redact(SAMPLE)
    assert " He led" not in out
    assert "they led" in out.lower()


def test_keeps_job_relevant_content():
    out = redact(SAMPLE)
    for keep in ("Python", "AWS", "PostgreSQL", "Kubernetes", "microservices"):
        assert keep in out


def test_contains_pii_gate():
    assert contains_pii("reach me at jane@doe.com")
    assert contains_pii("Gender: female")
    assert not contains_pii("Strong Python and SQL skills, 5 years experience")


def test_input_hash_is_stable():
    assert input_hash("a", "b") == input_hash("a", "b")
    assert input_hash("a", "b") != input_hash("ab", "")
