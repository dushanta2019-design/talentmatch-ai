"""Shared HTTP client for MCP servers → backend API."""

import os

import httpx

API_URL = os.environ.get("MCP_API_URL", "http://localhost:8000")
API_TOKEN = os.environ.get("MCP_API_TOKEN", "")


def client() -> httpx.Client:
    headers = {"Authorization": f"Bearer {API_TOKEN}"} if API_TOKEN else {}
    return httpx.Client(base_url=API_URL, headers=headers, timeout=120)


def get(path: str, **params) -> dict | list:
    with client() as c:
        r = c.get(path, params={k: v for k, v in params.items() if v is not None})
        r.raise_for_status()
        return r.json()


def post(path: str, json: dict | None = None) -> dict | list:
    with client() as c:
        r = c.post(path, json=json)
        r.raise_for_status()
        return r.json()
