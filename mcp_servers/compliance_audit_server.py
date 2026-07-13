"""MCP server: compliance + audit tools."""

import sys
from pathlib import Path

from mcp.server.fastmcp import FastMCP

import common

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.services.pii import contains_pii, redact  # noqa: E402

mcp = FastMCP("compliance_audit_server")


@mcp.tool()
def redact_text(text: str) -> str:
    """Apply the platform's PII/protected-attribute redaction to text:
    removes names, emails, phones, DOB, age, gender, religion, nationality,
    photos, and neutralizes gendered language."""
    return redact(text)


@mcp.tool()
def check_pii(text: str) -> dict:
    """Check whether text still contains PII that would block it from
    entering a training dataset."""
    return {"contains_pii": contains_pii(text)}


@mcp.tool()
def get_audit_logs(limit: int = 100) -> list[dict]:
    """Fetch recent audit-log entries — every AI parse, match, and human
    review is recorded with model version and input hash. (Admin token.)"""
    return common.get("/admin/audit-logs", limit=limit)


if __name__ == "__main__":
    mcp.run()
