# Compliance, Fairness & Privacy

This platform is **decision support, not decision making**. It never makes a
final hiring decision; every AI match must be reviewed by a human, and the UI
says so on every scoring surface.

## What the AI is never allowed to see or use

Scoring, embeddings, and LLM prompts operate **only on redacted text**
(`backend/app/services/pii.py`). Before any AI processing, we remove:

- Name (first resume line heuristic → `[CANDIDATE]`)
- Email, phone, URLs / social profiles
- Date of birth and age statements
- Declared gender, sex, marital status, religion, caste, race/ethnicity,
  nationality/citizenship, disability, blood group
- Photo references (embedded images in PDFs are never extracted at all —
  only text is parsed)
- Gendered language (pronouns and gendered titles are neutralized)

Two further defenses sit behind redaction:

1. **Schema whitelisting** — the LLM extraction schema (`ParsedResume`) has
   no fields for protected attributes, so they cannot enter structured data.
2. **Prompt rules** — every LLM call carries mandatory fairness instructions
   (`FAIRNESS_RULES` in `services/llm.py`) to ignore any residual signal and
   never infer protected attributes.

## Explainability

Every match returns, alongside the 0–100 score:

- A **confidence level** (low/medium/high) based on how much structured
  evidence was available — not on how high the score is.
- A per-dimension breakdown (semantic, skills, experience, education).
- Matched skills, missing skills, and explicit gap lists.
- An LLM-written explanation constrained to cite concrete, job-relevant
  evidence, ending with a fixed human-review disclaimer.

## Human oversight

Recruiters and hiring managers can **approve, reject, override the score, or
comment** on every match (`/feedback`). Overrides are displayed next to the
AI score, never silently replacing it.

## Audit trail

Every AI event (`resume.parsed`, `job.parsed`, `match.scored`,
`feedback.*`) writes an `audit_logs` row containing the actor, model version
(scoring algorithm + LLM + embedding model), and a SHA-256 hash of the
redacted inputs, so any score can be traced and reproduced.

## Feedback → training privacy gate

Recruiter feedback is only exported for training after:

1. `privacy_checked` — free-text comments are scanned by the PII detector;
   anything containing PII is permanently excluded from training.
2. Inputs in the dataset are the **redacted structured profiles**, never raw
   resumes.
3. A minimum dataset size (50 labeled examples) before any fine-tuning run
   is orchestrated.

## Monitoring for drift and disparate outcomes

`/admin/evaluate` compares AI scores against human labels (MAE, agreement
rate, precision@5). Falling agreement is the primary drift alarm. Because
protected attributes are never stored, group-level disparate-impact analysis
must be run as a **separate offline study** with explicit candidate consent
if legally required in your jurisdiction — do not add protected attributes to
this system to enable it.

## Data subject rights

- Candidates can delete their resumes (cascades to chunks and matches).
- Raw files live in S3 under per-upload UUID keys; deleting the DB row is the
  system of record — schedule S3 object deletion in the same operation for
  full erasure (see `routers/resumes.py`).
