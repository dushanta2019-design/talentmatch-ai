"""MCP server: resume parsing tools."""

from mcp.server.fastmcp import FastMCP

import common

mcp = FastMCP("resume_parser_server")


@mcp.tool()
def parse_resume_text(text: str) -> dict:
    """Submit raw resume text for parsing. PII is redacted before any AI
    processing; returns the resume record (parsing runs asynchronously —
    poll get_resume until status is 'ready')."""
    with common.client() as c:
        r = c.post("/resumes", data={"text": text})
        r.raise_for_status()
        return r.json()


@mcp.tool()
def get_resume(resume_id: str) -> dict:
    """Fetch a resume record including its parsed structured profile
    (skills, experience, education, certifications)."""
    return common.get(f"/resumes/{resume_id}")


if __name__ == "__main__":
    mcp.run()
