"""MCP server: deployment monitoring tools."""

from mcp.server.fastmcp import FastMCP

import common

mcp = FastMCP("deployment_monitor_server")


@mcp.tool()
def health_check() -> dict:
    """Liveness check for the API; also reports the active model version
    (scoring algorithm + LLM + embedding provider)."""
    return common.get("/health")


@mcp.tool()
def get_metrics() -> dict:
    """Request counters, error counts, and uptime for the running deployment."""
    return common.get("/metrics")


@mcp.tool()
def get_platform_stats() -> dict:
    """Business-level stats: user/resume/job counts, scored vs failed matches,
    review coverage, and average match score. (Admin token required.)"""
    return common.get("/admin/stats")


if __name__ == "__main__":
    mcp.run()
