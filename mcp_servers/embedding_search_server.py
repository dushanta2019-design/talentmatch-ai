"""MCP server: embedding + semantic vector search tools.

Ranks parsed resumes against arbitrary query text using the same embedding
provider as the platform (Voyage in prod, local fallback in dev).
"""

import sys
from pathlib import Path

from mcp.server.fastmcp import FastMCP

import common

# Reuse the backend's embedding provider directly for query-time embedding.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.services.embeddings import cosine_similarity, embed_text  # noqa: E402

mcp = FastMCP("embedding_search_server")


@mcp.tool()
def embed(text: str) -> list[float]:
    """Embed text with the platform's embedding model. Useful for building
    custom similarity workflows."""
    return embed_text(text)


@mcp.tool()
def semantic_search_resumes(query: str, top_k: int = 10) -> list[dict]:
    """Semantic search over parsed resumes: ranks resumes by similarity of
    their (redacted) content to the query text."""
    query_vec = embed_text(query)
    resumes = common.get("/resumes")
    scored = []
    for r in resumes:
        if r.get("status") != "ready" or not r.get("parsed"):
            continue
        doc = " ".join(
            r["parsed"].get("skills", []) + [r["parsed"].get("summary", "")]
        )
        sim = cosine_similarity(query_vec, embed_text(doc))
        scored.append({"resume_id": r["id"], "file_name": r.get("file_name"),
                       "similarity": round(sim, 4)})
    scored.sort(key=lambda x: x["similarity"], reverse=True)
    return scored[:top_k]


if __name__ == "__main__":
    mcp.run()
