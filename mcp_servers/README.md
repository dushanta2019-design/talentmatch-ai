# MCP Tool Servers

Eight MCP (Model Context Protocol) servers that expose the resume-matching
platform as agent-callable tools. Each is a standalone stdio server built on
FastMCP and talks to the backend REST API with a service account token.

| Server | Tools |
|---|---|
| `resume_parser_server` | `parse_resume_text`, `get_resume` |
| `jd_parser_server` | `parse_job_description`, `create_job` |
| `embedding_search_server` | `semantic_search_resumes`, `embed_text` |
| `match_scoring_server` | `score_match`, `rank_candidates_for_job`, `rank_jobs_for_resume` |
| `feedback_training_server` | `record_feedback`, `export_training_dataset` |
| `evaluation_server` | `run_evaluation`, `list_evaluations` |
| `deployment_monitor_server` | `health_check`, `get_metrics` |
| `compliance_audit_server` | `redact_text`, `check_pii`, `get_audit_logs` |

## Setup

```bash
pip install -r requirements.txt
export MCP_API_URL=http://localhost:8000
export MCP_API_TOKEN=<JWT for a service account (admin role for admin tools)>
python resume_parser_server.py     # or register in your MCP client config
```

## Claude Desktop / Claude Code config example

```json
{
  "mcpServers": {
    "resume-matching": {
      "command": "python",
      "args": ["mcp_servers/match_scoring_server.py"],
      "env": { "MCP_API_URL": "http://localhost:8000", "MCP_API_TOKEN": "..." }
    }
  }
}
```
