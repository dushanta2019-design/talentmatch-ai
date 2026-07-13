"""MCP server: feedback capture + retraining orchestration tools."""

from mcp.server.fastmcp import FastMCP

import common

mcp = FastMCP("feedback_training_server")


@mcp.tool()
def record_feedback(match_id: str, action: str, label_score: int | None = None,
                    comment: str | None = None) -> dict:
    """Record human review of an AI match. action: approve | reject |
    override | comment. 'override' requires label_score (0-100). Feedback
    only enters training data after passing the privacy check."""
    return common.post("/feedback", {
        "match_id": match_id, "action": action,
        "label_score": label_score, "comment": comment,
    })


@mcp.tool()
def export_training_dataset() -> dict:
    """Run the privacy gate over accumulated feedback and export a PII-free
    labeled dataset for fine-tuning. Returns status 'insufficient_data' if
    fewer than the minimum labeled examples exist. (Admin token required.)"""
    return common.post("/admin/training/export")


@mcp.tool()
def list_training_runs() -> list[dict]:
    """List past training-dataset exports and their statuses."""
    return common.get("/admin/training/runs")


if __name__ == "__main__":
    mcp.run()
