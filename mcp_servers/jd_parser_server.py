"""MCP server: job-description parsing tools."""

from mcp.server.fastmcp import FastMCP

import common

mcp = FastMCP("jd_parser_server")


@mcp.tool()
def create_job(title: str, description: str, company: str | None = None,
               location: str | None = None) -> dict:
    """Create a job description. Parsing into structured requirements
    (required/preferred skills, min experience, education) runs asynchronously —
    poll parse_job_description until status is 'ready'."""
    return common.post("/jobs", {
        "title": title, "description": description,
        "company": company, "location": location,
    })


@mcp.tool()
def parse_job_description(job_id: str) -> dict:
    """Fetch a job record including its parsed structured requirements."""
    return common.get(f"/jobs/{job_id}")


if __name__ == "__main__":
    mcp.run()
