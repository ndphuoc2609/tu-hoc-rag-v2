"""OpenRouter client: chat (Luna) + embeddings. Stdlib only (urllib).

Key KHONG nam trong file nay: doc tu env OPENROUTER_API_KEY (Render env var
hoac file .env local). Khong bao gio in key ra log.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
for _line in (BASE / ".env").read_text(encoding="utf-8").splitlines() if (BASE / ".env").exists() else []:
    if "=" in _line and not _line.strip().startswith("#"):
        _k, _v = _line.split("=", 1)
        os.environ.setdefault(_k.strip(), _v.strip().strip('"').strip("'"))

OPENROUTER_KEY = os.environ.get("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.environ.get("OPENROUTER_MODEL", "openai/gpt-6-luna")
EMBED_MODEL = os.environ.get("OPENROUTER_EMBED_MODEL", "openai/text-embedding-3-small")
EMBED_DIMS = 1536
CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"
EMBED_URL = "https://openrouter.ai/api/v1/embeddings"


def has_key() -> bool:
    return bool(OPENROUTER_KEY)


def _post(url: str, payload: dict, timeout: int = 60) -> dict | None:
    if not OPENROUTER_KEY:
        return None
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {OPENROUTER_KEY}")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as res:
            return json.loads(res.read())
    except Exception:
        return None


def chat(messages, temperature: float = 0.2, max_tokens: int = 1000) -> str | None:
    """Tra ve content string, hoac None neu khong key / loi. Khong raise."""
    out = _post(CHAT_URL, {"model": OPENROUTER_MODEL, "messages": messages,
                           "temperature": temperature, "max_tokens": max_tokens})
    if not out:
        return None
    try:
        return out["choices"][0]["message"]["content"]
    except Exception:
        return None


def embed(texts: list[str]) -> list[list[float] | None]:
    """Embed 1 batch (toi da ~20 text). Tra list cung do dai, None neu loi tung item."""
    if not texts or not OPENROUTER_KEY:
        return [None] * len(texts)
    out = _post(EMBED_URL, {"model": EMBED_MODEL, "input": texts}, timeout=120)
    if not out:
        return [None] * len(texts)
    try:
        by_idx = {d["index"]: d["embedding"] for d in out.get("data", [])}
        return [by_idx.get(i) for i in range(len(texts))]
    except Exception:
        return [None] * len(texts)


def extract_json(text: str):
    """Lay khoi JSON dau tien trong text LLM tra ve (object hoac list)."""
    if not text:
        return None
    for open_c, close_c in (("{", "}"), ("[", "]")):
        a, b = text.find(open_c), text.rfind(close_c)
        if 0 <= a < b:
            try:
                return json.loads(text[a:b + 1])
            except Exception:
                pass
    return None
