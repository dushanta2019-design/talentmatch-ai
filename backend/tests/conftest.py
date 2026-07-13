import os

# Deterministic local embeddings; no external services needed for unit tests.
os.environ.setdefault("EMBEDDING_PROVIDER", "local")
os.environ.setdefault("SECRET_KEY", "test-secret-key-that-is-long-enough-for-hs256")
