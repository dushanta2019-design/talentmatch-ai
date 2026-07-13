"""MCP server: match scoring and ranking tools."""

from mcp.server.fastmcp import FastMCP

import common

mcp = FastMCP("match_scoring_server")


@mcp.tool()
def score_match(resume_id: str, job_id: str) -> dict:
    """Request an AI match between one resume and one job description.
    Returns the match record (scoring runs asynchronously — poll get_match).
    Scores are decision support only; a human reviewer makes final calls."""
    return common.post("/matches", {"resume_id": resume_id, "job_id": job_id})


@mcp.tool()
def get_match(match_id: str) -> dict:
    """Fetch a match: 0-100 score, confidence level, per-dimension breakdown,
    matched/missing skills, gaps, and the evidence-based explanation."""
    return common.get(f"/matches/{match_id}")


@mcp.tool()
def rank_candidates_for_job(job_id: str) -> list[dict]:
    """Ranked list of candidates for a job, highest match score first."""
    return common.get(f"/matches/job/{job_id}")


@mcp.tool()
def rank_jobs_for_resume(resume_id: str) -> list[dict]:
    """Ranked list of jobs for a candidate, highest match score first."""
    return common.get(f"/matches/resume/{resume_id}")


@mcp.tool()
def batch_match_job(job_id: str, limit: int = 25) -> list[dict]:
    """Match one job against many resumes at once (async scoring)."""
    return common.post("/matches/batch", {"job_id": job_id, "limit": limit})


if __name__ == "__main__":
    mcp.run()
