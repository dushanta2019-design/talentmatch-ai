"""Embedding pipeline with pluggable providers.

- "voyage": Voyage AI (voyage-3, 1024-dim) — production semantic quality.
  (Anthropic does not provide an embeddings endpoint; Voyage is the
  recommended pairing with Claude.)
- "local": deterministic hashed bag-of-features embedder — zero-dependency
  fallback for dev machines and CI. Not semantically strong, but stable.
"""

import hashlib
import math
import re

from app.config import get_settings

_TOKEN_RE = re.compile(r"[a-z0-9+#.]+")


def _local_embed(text: str, dim: int) -> list[float]:
    vec = [0.0] * dim
    tokens = _TOKEN_RE.findall(text.lower())
    for i, tok in enumerate(tokens):
        for gram in (tok, tokens[i - 1] + "_" + tok if i else tok):
            h = int.from_bytes(hashlib.md5(gram.encode()).digest()[:8], "big")
            vec[h % dim] += 1.0 if (h >> 63) else -1.0
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def embed_texts(texts: list[str]) -> list[list[float]]:
    settings = get_settings()
    if settings.embedding_provider == "voyage":
        import voyageai

        client = voyageai.Client(api_key=settings.voyage_api_key)
        result = client.embed(texts, model=settings.embedding_model, input_type="document")
        return result.embeddings
    return [_local_embed(t, settings.embedding_dim) for t in texts]


def embed_text(text: str) -> list[float]:
    return embed_texts([text])[0]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(y * y for y in b)) or 1.0
    return dot / (na * nb)


def chunk_text(text: str, max_chars: int = 1500, overlap: int = 200) -> list[str]:
    """Paragraph-aware chunking for chunk-level semantic search."""
    if len(text) <= max_chars:
        return [text] if text.strip() else []
    chunks, start = [], 0
    while start < len(text):
        end = min(start + max_chars, len(text))
        if end < len(text):
            brk = text.rfind("\n", start, end)
            if brk > start + max_chars // 2:
                end = brk
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start = max(end - overlap, start + 1)
        if end >= len(text):
            break
    return chunks
