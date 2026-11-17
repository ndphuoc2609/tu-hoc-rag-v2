#!/usr/bin/env python3
"""Smoke test v2: logic thuan (khong can DB, khong can key).
Chay: python3 tests/test_smoke_v2.py  (chay tu thu muc tu-hoc-rag-v2/)
Kiem tra: chunk, tokenize, TF-IDF, rubric, hash password, fallback quiz.
Flow API day du can Postgres that — xem README (curl).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend import rag  # noqa: E402
from backend.auth import check_password, hash_password  # noqa: E402

TEXT = ("Quang hợp là quá trình cây xanh dùng ánh sáng để tổng hợp chất hữu cơ. "
        "Quang hợp diễn ra ở lá cây. Pha sáng cần ánh sáng mặt trời. "
        "Pha tối xảy ra ở chất nền của lục lạp và không cần ánh sáng.")
assert len(rag.chunk_text("\n\n".join([TEXT] * 6))) >= 2, "chunk phai cat duoc van ban dai"
assert "quang" in rag.tokenize("Quang hợp là gì?"), "tokenize mat dau tieng Viet"

chunks = [{"id": 1, "text": TEXT},
          {"id": 2, "text": "Đạo hàm của x bình phương là hai x. Tích phân dùng để tính diện tích."}]
top = rag.tfidf_rank(chunks, "quang hợp là gì")
assert top and top[0]["id"] == 1, f"TF-IDF phai tim dung chunk quang hop: {top}"

r = rag.parse_rubric("Ý 1 - 2đ\nÝ 2 - 3đ")
assert len(r) == 2 and r[0]["max"] == 2.0 and sum(x["max"] for x in r) == 5.0, f"rubric sai: {r}"
r2 = rag.parse_rubric([{"criterion": "Nội dung", "max": 4}])
assert r2[0]["max"] == 4.0

h = hash_password("123456")
assert h.startswith("pbkdf2$") and check_password("123456", h) and not check_password("sai", h)

qs = rag.fallback_quiz(chunks, n=2)
assert qs and len(qs[0]["options"]) == 4, f"fallback quiz phai co 4 options: {qs}"
assert rag.file_hash("a") == rag.file_hash("a") and rag.file_hash("a") != rag.file_hash("b")

print("smoke v2 logic: OK — chunk/tokenize/tfidf/rubric/auth/quiz/hash pass")
