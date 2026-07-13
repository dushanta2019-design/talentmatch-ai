"""MCP server: model evaluation tools."""

from mcp.server.fastmcp import FastMCP

import common

mcp = FastMCP("evaluation_server")


@mcp.tool()
def run_evaluation() -> dict:
    """Evaluate the current scoring model against recruiter feedback:
    MAE vs override labels, agreement rate with approve/reject decisions,
    and precision@5 on per-job rankings. (Admin token required.)"""
    return common.post("/admin/evaluate")


@mcp.tool()
def list_evaluations() -> list[dict]:
    """List historical evaluation runs with their metric snapshots, useful
    for detecting model drift over time."""
    return common.get("/admin/evaluations")


if __name__ == "__main__":
    mcp.run()
