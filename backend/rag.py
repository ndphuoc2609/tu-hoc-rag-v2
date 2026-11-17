"""RAG helpers: chunk, tokenize, trich text PDF/DOCX/TXT, retrieval hybrid.

Retrieval: vector (pgvector, neu co) + FTS (to_tsvector) + TF-IDF fallback
trong Python. Khong co key embedding -> embedding NULL, van tim duoc bang FTS.
"""
from __future__ import annotations

import hashlib
import io
import math
import random
import re

TOKEN_RE = re.compile(r"[a-z0-9à-ỹ]+", re.I)


def tokenize(s: str):
    return TOKEN_RE.findall(s.lower())


def chunk_text(text: str, size: int = 1000, overlap: int = 150):
    """Cat theo doan van, du `size` ky tu moi cat, giu overlap.
    ponytail: ceiling — khong cat theo cau ngu nghia; tai lieu co bang bieu
    phuc tap can chunk theo heading (upgrade path)."""
    out, buf = [], ""
    for p in text.split("\n"):
        p = p.strip()
        if not p:
            continue
        if len(buf) + len(p) + 1 > size and buf:
            out.append(buf)
            buf = buf[-overlap:] if len(buf) > overlap else buf
        buf = (buf + "\n" + p).strip() if buf else p
    if buf:
        out.append(buf)
    return [x for x in out if len(x.strip()) > 20]


def file_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def extract_text(filename: str, data: bytes) -> str:
    """Trich text theo duoi file. Chi trich text, khong OCR anh."""
    name = filename.lower()
    if name.endswith(".pdf"):
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(data))
        return "\n".join((p.extract_text() or "") for p in reader.pages)
    if name.endswith(".docx"):
        from docx import Document
        return "\n".join(p.text for p in Document(io.BytesIO(data)).paragraphs)
    # .txt / .md / khac: doc nhu text
    return data.decode("utf-8", errors="replace")


def tfidf_rank(chunks: list[dict], query: str, k: int = 5):
    """chunks: [{id, text}]. Tra top-k [{id, text, score}] theo TF-IDF."""
    if not chunks:
        return []
    docs = [(c["id"], c["text"], tokenize(c["text"])) for c in chunks]
    n = len(docs)
    df: dict[str, int] = {}
    for _, _, toks in docs:
        for t in set(toks):
            df[t] = df.get(t, 0) + 1
    qtoks = set(tokenize(query))
    scored = []
    for cid, text, toks in docs:
        tf: dict[str, int] = {}
        for t in toks:
            tf[t] = tf.get(t, 0) + 1
        s = sum(tf.get(t, 0) * (math.log((n + 1) / (df.get(t, 0) + 1)) + 1) for t in qtoks)
        scored.append((s, cid, text))
    scored.sort(reverse=True)
    return [{"id": cid, "text": text, "score": round(s, 3)}
            for s, cid, text in scored[:k] if s > 0]


def fallback_quiz(chunks: list[dict], n: int = 5):
    """Khong key LLM -> cloze: khoet 1 tu khoa trong cau, 3 tu khac lam nhieu.
    ponytail: so cau bi gioi han boi so tu khoa khac nhau trong tai lieu;
    muon du 5 cau voi doc ngan thi can LLM (upgrade: sinh tu LLM)."""
    rows = [c["text"] for c in chunks]
    vocab = sorted({t for r in rows for t in tokenize(r) if len(t) >= 4})
    out, used = [], set()
    for text in rows:
        for sent in re.split(r"[.\n]", text):
            if len(out) >= n:
                break
            toks = [t for t in sent.split() if len(re.sub(r"[^a-zà-ỹ]", "", t.lower())) >= 4]
            if len(toks) < 6:
                continue
            kw = max(toks, key=len)
            clean = re.sub(r"[^a-zà-ỹ]", "", kw.lower())
            if clean in used:
                continue
            used.add(clean)
            others = [v for v in vocab if v != clean]
            random.shuffle(others)
            opts = [clean] + others[:3]
            random.shuffle(opts)
            out.append({"question": sent.strip().replace(kw, "______"),
                        "options": opts, "answer_idx": opts.index(clean),
                        "explanation": f"Từ đúng là '{clean}' theo tài liệu.",
                        "source": sent.strip()[:200]})
    return out


def parse_rubric(rubric):
    """Nhan list [{criterion, max}] hoac string moi dong 'Ý - 2đ'."""
    if isinstance(rubric, list):
        return [{"criterion": str(x.get("criterion", x)), "max": float(x.get("max", 1))}
                for x in rubric]
    if isinstance(rubric, str):
        items = []
        for line in rubric.splitlines():
            m = re.match(r"\s*(.+?)\s*[-:]\s*(\d+(?:[.,]\d+)?)\s*đ?", line.strip())
            if m:
                items.append({"criterion": m.group(1), "max": float(m.group(2).replace(",", "."))})
        return items or [{"criterion": rubric.strip() or "Nội dung", "max": 10.0}]
    return [{"criterion": "Nội dung", "max": 10.0}]
