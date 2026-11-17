#!/usr/bin/env python3
"""API test v2: hybrid path + chat 2 che do. Can Postgres that qua pgserver, KHONG can key.
Chay tu thu muc tu-hoc-rag-v2: .venv/bin/python tests/test_api_v2.py
Luu y: pgserver chay postgres duoi user 'pgserver' nen can doc duoc lib trong
.venv/.../pgserver.libs (neu loi libpq: chmod -R o+rX .../pgserver.libs .../pgserver
+ them duong dan vao /etc/ld.so.conf.d roi ldconfig).
"""
import json
import os
import shutil
import sys
import tempfile

os.environ["OPENROUTER_API_KEY"] = ""  # mo phong khong key
import pgserver  # noqa: E402

TMP = tempfile.mkdtemp(prefix="tuhoc-test-")
SRV = pgserver.get_server(os.path.join(TMP, "pgdata"))
os.environ["DATABASE_URL"] = SRV.get_uri()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient  # noqa: E402
from backend import db  # noqa: E402
from backend.main import _validate_changes, _validate_outline, app  # noqa: E402

DOC_A = ("Quang hợp diễn ra ở lá cây. Pha sáng cần ánh sáng mặt trời. "
         "Pha tối xảy ra ở chất nền của lục lạp và không cần ánh sáng. ") * 6
DOC_B = ("Đạo hàm của hàm số đo tốc độ thay đổi. Đạo hàm của x bình phương bằng hai x. "
         "Tích phân dùng để tính diện tích dưới đường cong. ") * 6

passed = []


def check(name, cond, extra=""):
    assert cond, f"FAIL {name}: {extra}"
    passed.append(name)
    print(f"  ok {name}")


def main():
    with TestClient(app) as cl:
        # --- auth ---
        r = cl.post("/api/auth/register", json={
            "name": "Test", "email": "t@test.vn", "password": "123456", "role": "student"})
        assert r.status_code == 200, r.text
        uid = r.json()["user"]["id"]
        H = {"Authorization": f"Bearer {r.json()['token']}"}
        print("auth ok")

        # --- 1. tao mon khong key -> khung generic + outline null ---
        r = cl.post("/api/subjects", json={"name": "Hóa 11"}, headers=H)
        assert r.status_code == 200, r.text
        sid = r.json()["id"]
        check("create-no-key-outline-null", r.json()["outline_proposal"] is None, r.text)
        ch = cl.get(f"/api/subjects/{sid}/chapters", headers=H).json()
        check("create-generic-3-chapters", len(ch) == 3
              and ch[0]["title"] == "Chương 1: Kiến thức nền tảng", ch)
        ls = cl.get(f"/api/subjects/{sid}/lessons", params={"chapter": 1}, headers=H).json()
        check("create-generic-5-lessons", len(ls) == 5 and ls[0]["title"] == "Bài 1", ls)

        # --- 2. tao mon co level ---
        r = cl.post("/api/subjects", json={"name": "Sinh 10", "level": "Lớp 10"}, headers=H)
        check("create-with-level", r.status_code == 200
              and r.json()["outline_proposal"] is None, r.text)
        sid2 = r.json()["id"]

        # --- 3. refresh chua co doc -> 400; proposal -> null ---
        r = cl.post(f"/api/subjects/{sid}/path/refresh", json={}, headers=H)
        check("refresh-no-docs-400", r.status_code == 400, r.text)
        r = cl.get(f"/api/subjects/{sid}/path/proposal", headers=H)
        check("get-proposal-null", r.status_code == 200 and r.json()["proposal"] is None, r.text)

        # --- 4. up 2 doc khac tu khoa ---
        r = cl.post(f"/api/subjects/{sid}/docs", json={"title": "Quang hop", "text": DOC_A}, headers=H)
        assert r.status_code == 200, r.text
        doc_a = r.json()["id"]
        check("upload-doc-A", r.json()["status"] == "done" and r.json()["chunks"] >= 1, r.text)
        r = cl.post(f"/api/subjects/{sid}/docs", json={"title": "Dao ham", "text": DOC_B}, headers=H)
        assert r.status_code == 200, r.text
        doc_b = r.json()["id"]

        # --- 4b. GET docs cua mon ---
        r = cl.get(f"/api/subjects/{sid}/docs", headers=H)
        got = r.json()
        check("list-docs-2", r.status_code == 200 and len(got) == 2
              and [d["id"] for d in got] == [doc_a, doc_b]
              and [d["title"] for d in got] == ["Quang hop", "Dao ham"]
              and all(d["status"] == "done" and d["chunks"] >= 1 for d in got)
              and all("created_at" in d for d in got), r.text)
        r = cl.get("/api/subjects/999999/docs", headers=H)
        check("list-docs-unknown-404", r.status_code == 404, r.text)
        r = cl.get(f"/api/subjects/{sid2}/docs", headers=H)
        check("list-docs-other-empty", r.status_code == 200 and r.json() == [], r.text)

        # --- 5. refresh co doc nhung khong key -> 503 ---
        r = cl.post(f"/api/subjects/{sid}/path/refresh", json={}, headers=H)
        check("refresh-no-key-503", r.status_code == 503
              and "OpenRouter" in r.json().get("detail", ""), r.text)

        # --- 6. apply proposal (chen truc tiep vao DB) ---
        ch1_id = None
        with db.connect() as c:
            ch1_id = c.execute("SELECT id FROM chapters WHERE subject_id=%s AND n=1",
                               (sid,)).fetchone()["id"]
            pid = c.execute(
                "INSERT INTO path_proposals(subject_id, user_id, kind, payload, status, created_at) "
                "VALUES(%s,%s,'refresh',%s,'pending',%s) RETURNING id",
                (sid, uid, json.dumps({"changes": [
                    {"id": "c1", "type": "rename_chapter", "chapter_n": 1,
                     "title": "Đại cương hóa học", "old_title": "Chương 1: Kiến thức nền tảng"},
                    {"id": "c2", "type": "add_chapter", "title": "Nhiệt hóa học",
                     "source_doc_id": doc_a,
                     "lessons": [{"n": 1, "title": "Enthalpy"}, {"n": 2, "title": "Entropy"}]},
                    {"id": "c3", "type": "rename_lesson", "chapter_n": 2, "lesson_n": 1,
                     "title": "Bài mở đầu"},
                ]}, ensure_ascii=False), db.now_iso())).fetchone()["id"]
        r = cl.get(f"/api/subjects/{sid}/path/proposal", headers=H)
        check("get-proposal-pending", r.json()["proposal"]["id"] == pid
              and len(r.json()["proposal"]["changes"]) == 3, r.text)
        r = cl.post(f"/api/subjects/{sid}/path/proposals/{pid}/apply",
                    json={"change_ids": ["c1", "c2"]}, headers=H)
        check("apply-c1-c2", r.status_code == 200 and r.json() == {
            "applied": ["c1", "c2"], "proposal_status": "applied"}, r.text)
        with db.connect() as c:
            row = c.execute("SELECT id, title FROM chapters WHERE subject_id=%s AND n=1",
                            (sid,)).fetchone()
            check("rename-keeps-id", row["id"] == ch1_id
                  and row["title"] == "Đại cương hóa học", row)
            new = c.execute("SELECT id, title FROM chapters WHERE subject_id=%s AND n=4",
                            (sid,)).fetchone()
            check("add-chapter-appended", new and new["title"] == "Nhiệt hóa học", new)
            lsn = c.execute("SELECT title, source_doc_id FROM lessons WHERE chapter_id=%s ORDER BY n",
                            (new["id"],)).fetchall()
            check("add-chapter-lessons+source", [dict(x) for x in lsn] == [
                {"title": "Enthalpy", "source_doc_id": doc_a},
                {"title": "Entropy", "source_doc_id": doc_a}], lsn)
            l21 = c.execute(
                "SELECT title FROM lessons WHERE chapter_id=("
                "SELECT id FROM chapters WHERE subject_id=%s AND n=2) AND n=1",
                (sid,)).fetchone()
            check("unselected-change-untouched", l21["title"] == "Bài 1", l21)
        r = cl.post(f"/api/subjects/{sid}/path/proposals/{pid}/apply",
                    json={"change_ids": ["c3"]}, headers=H)
        check("reapply-400", r.status_code == 400, r.text)
        r = cl.post(f"/api/subjects/{sid}/path/proposals/999999/apply",
                    json={"change_ids": ["c1"]}, headers=H)
        check("apply-unknown-404", r.status_code == 404, r.text)
        # apply rong -> rejected, khong doi gi
        with db.connect() as c:
            pid2 = c.execute(
                "INSERT INTO path_proposals(subject_id, user_id, kind, payload, status, created_at) "
                "VALUES(%s,%s,'refresh',%s,'pending',%s) RETURNING id",
                (sid, uid, json.dumps({"changes": [
                    {"id": "c1", "type": "remove_chapter", "chapter_n": 4}]},
                    ensure_ascii=False), db.now_iso())).fetchone()["id"]
        r = cl.post(f"/api/subjects/{sid}/path/proposals/{pid2}/apply",
                    json={"change_ids": []}, headers=H)
        check("apply-empty-rejected", r.json() == {"applied": [], "proposal_status": "rejected"},
              r.text)
        with db.connect() as c:
            check("rejected-keeps-chapter",
                  c.execute("SELECT 1 FROM chapters WHERE subject_id=%s AND n=4",
                            (sid,)).fetchone() is not None)
            # proposal cua mon khac -> 404 khi apply tu mon nay
            pid3 = c.execute(
                "INSERT INTO path_proposals(subject_id, user_id, kind, payload, status, created_at) "
                "VALUES(%s,%s,'refresh',%s,'pending',%s) RETURNING id",
                (sid2, uid, json.dumps({"changes": []}, ensure_ascii=False),
                 db.now_iso())).fetchone()["id"]
        r = cl.post(f"/api/subjects/{sid}/path/proposals/{pid3}/apply",
                    json={"change_ids": []}, headers=H)
        check("apply-other-subject-404", r.status_code == 404, r.text)

        # --- 6b. outline apply THAY THE khung generic (khong append) ---
        def _outline_pid(sid_x, changes):
            with db.connect() as c:
                return c.execute(
                    "INSERT INTO path_proposals(subject_id, user_id, kind, payload, status, created_at) "
                    "VALUES(%s,%s,'outline',%s,'pending',%s) RETURNING id",
                    (sid_x, uid, json.dumps({"changes": changes}, ensure_ascii=False),
                     db.now_iso())).fetchone()["id"]

        outline2 = [
            {"id": "c1", "type": "add_chapter", "chapter_n": 1, "title": "Dao động cơ",
             "lessons": [{"n": 1, "title": "Dao động điều hòa"}, {"n": 2, "title": "Con lắc lò xo"}]},
            {"id": "c2", "type": "add_chapter", "chapter_n": 2, "title": "Sóng cơ",
             "lessons": [{"n": 1, "title": "Sóng ngang và sóng dọc"}]},
        ]
        r = cl.post("/api/subjects", json={"name": "Lý 11"}, headers=H)
        assert r.status_code == 200, r.text
        sid_o = r.json()["id"]
        ch = cl.get(f"/api/subjects/{sid_o}/chapters", headers=H).json()
        check("outline-before-generic-3", len(ch) == 3
              and ch[0]["title"] == "Chương 1: Kiến thức nền tảng", ch)
        # apply rong -> rejected, khung generic con nguyen (khong xoa)
        pid_oe = _outline_pid(sid_o, outline2)
        r = cl.post(f"/api/subjects/{sid_o}/path/proposals/{pid_oe}/apply",
                    json={"change_ids": []}, headers=H)
        check("outline-apply-empty-rejected",
              r.json() == {"applied": [], "proposal_status": "rejected"}, r.text)
        ch = cl.get(f"/api/subjects/{sid_o}/chapters", headers=H).json()
        check("outline-rejected-keeps-generic", len(ch) == 3, ch)
        # apply ca 2 -> chi con 2 chuong AI, dung thu tu + bai
        pid_o = _outline_pid(sid_o, outline2)
        r = cl.post(f"/api/subjects/{sid_o}/path/proposals/{pid_o}/apply",
                    json={"change_ids": ["c1", "c2"]}, headers=H)
        check("outline-apply-both", r.status_code == 200 and r.json() == {
            "applied": ["c1", "c2"], "proposal_status": "applied"}, r.text)
        ch = cl.get(f"/api/subjects/{sid_o}/chapters", headers=H).json()
        check("outline-replaces-generic", len(ch) == 2
              and [(x["n"], x["title"]) for x in ch] == [(1, "Dao động cơ"), (2, "Sóng cơ")], ch)
        ls = cl.get(f"/api/subjects/{sid_o}/lessons", params={"chapter": 1}, headers=H).json()
        check("outline-lessons",
              [x["title"] for x in ls] == ["Dao động điều hòa", "Con lắc lò xo"], ls)
        with db.connect() as c:
            check("outline-no-generic-left",
                  c.execute("SELECT 1 FROM chapters WHERE subject_id=%s AND title LIKE 'Chương %%'",
                            (sid_o,)).fetchone() is None)
        # apply outline chi 1 trong 2 chuong -> mon chi con 1 chuong do
        r = cl.post("/api/subjects", json={"name": "Sử 11"}, headers=H)
        sid_o2 = r.json()["id"]
        pid_o2 = _outline_pid(sid_o2, outline2)
        r = cl.post(f"/api/subjects/{sid_o2}/path/proposals/{pid_o2}/apply",
                    json={"change_ids": ["c2"]}, headers=H)
        check("outline-apply-one", r.status_code == 200 and r.json() == {
            "applied": ["c2"], "proposal_status": "applied"}, r.text)
        ch = cl.get(f"/api/subjects/{sid_o2}/chapters", headers=H).json()
        check("outline-partial-one-chapter", len(ch) == 1
              and ch[0]["n"] == 2 and ch[0]["title"] == "Sóng cơ", ch)

        # --- 6c. add_lesson ton trong lesson_n, trung thi don len ---
        with db.connect() as c:
            pid_l = c.execute(
                "INSERT INTO path_proposals(subject_id, user_id, kind, payload, status, created_at) "
                "VALUES(%s,%s,'refresh',%s,'pending',%s) RETURNING id",
                (sid, uid, json.dumps({"changes": [
                    {"id": "c1", "type": "add_lesson", "chapter_n": 2, "lesson_n": 1,
                     "title": "Bài thêm trùng n"},
                    {"id": "c2", "type": "add_lesson", "chapter_n": 2, "lesson_n": 9,
                     "title": "Bài thêm n=9"},
                    {"id": "c3", "type": "add_lesson", "chapter_n": 2,
                     "title": "Bài thêm append"},
                ]}, ensure_ascii=False), db.now_iso())).fetchone()["id"]
        r = cl.post(f"/api/subjects/{sid}/path/proposals/{pid_l}/apply",
                    json={"change_ids": ["c1", "c2", "c3"]}, headers=H)
        check("add-lesson-apply", r.status_code == 200 and r.json() == {
            "applied": ["c1", "c2", "c3"], "proposal_status": "applied"}, r.text)
        with db.connect() as c:
            lsn = c.execute(
                "SELECT n, title FROM lessons WHERE chapter_id=("
                "SELECT id FROM chapters WHERE subject_id=%s AND n=2) ORDER BY n",
                (sid,)).fetchall()
            check("add-lesson-n-respected-and-bumped",
                  [(x["n"], x["title"]) for x in lsn] == [
                      (1, "Bài 1"), (2, "Bài 2"), (3, "Bài 3"), (4, "Bài 4"), (5, "Bài 5"),
                      (6, "Bài thêm trùng n"), (9, "Bài thêm n=9"), (10, "Bài thêm append")], lsn)

        # --- 7. chat rag khong key ---
        r = cl.post(f"/api/subjects/{sid}/chat", json={"question": "quang hợp"}, headers=H)
        check("chat-rag-default", r.status_code == 200
              and r.json()["mode"] == "retrieval_only"
              and r.json()["sources"]
              and r.json()["sources"][0]["doc_id"] == doc_a
              and r.json()["sources"][0]["doc_title"] == "Quang hop", r.text)
        r = cl.post(f"/api/subjects/{sid}/chat",
                    json={"question": "thuyết tương đối"}, headers=H)
        check("chat-rag-no-context", r.json()["mode"] == "no_context"
              and r.json()["sources"] == [], r.text)

        # --- 8. chat general / auto khong key ---
        r = cl.post(f"/api/subjects/{sid}/chat",
                    json={"question": "thủ đô của Pháp là gì", "mode": "general"}, headers=H)
        check("chat-general-unavailable", r.json()["mode"] == "general_unavailable"
              and r.json()["sources"] == [], r.text)
        r = cl.post(f"/api/subjects/{sid}/chat",
                    json={"question": "quang hợp", "mode": "auto"}, headers=H)
        check("chat-auto-hit-retrieval-only", r.json()["mode"] == "retrieval_only"
              and r.json()["sources"], r.text)
        r = cl.post(f"/api/subjects/{sid}/chat",
                    json={"question": "thuyết tương đối", "mode": "auto"}, headers=H)
        check("chat-auto-nohit-no-key", r.json()["mode"] == "no_context", r.text)
        r = cl.post(f"/api/subjects/{sid}/chat",
                    json={"question": "quang hợp", "mode": "bogus"}, headers=H)
        check("chat-unknown-mode-defaults-rag", r.json()["mode"] == "retrieval_only", r.text)

        # --- 9. chat doc_id ---
        r = cl.post(f"/api/subjects/{sid}/chat",
                    json={"question": "quang hợp", "doc_id": doc_b}, headers=H)
        check("chat-doc-filter-no-hit", r.json()["mode"] == "no_context", r.text)
        r = cl.post(f"/api/subjects/{sid}/chat",
                    json={"question": "đạo hàm", "doc_id": doc_b}, headers=H)
        check("chat-doc-filter-hit", r.json()["mode"] == "retrieval_only"
              and r.json()["sources"]
              and all(s["doc_id"] == doc_b for s in r.json()["sources"]), r.text)
        r = cl.post(f"/api/subjects/{sid}/chat",
                    json={"question": "đạo hàm", "doc_id": 999999}, headers=H)
        check("chat-doc-unknown-404", r.status_code == 404, r.text)

        # --- 9b. TF-IDF fallback (FTS AND khong khop -> roi ve TF-IDF) ---
        r = cl.post(f"/api/subjects/{sid}/chat",
                    json={"question": "quang zzzqqq"}, headers=H)
        check("chat-tfidf-fallback", r.json()["mode"] == "retrieval_only"
              and r.json()["sources"][0]["doc_id"] == doc_a, r.text)
        r = cl.post(f"/api/subjects/{sid}/chat",
                    json={"question": "quang zzzqqq", "doc_id": doc_b}, headers=H)
        check("chat-tfidf-doc-filter", r.json()["mode"] == "no_context", r.text)

        # --- 9c. vector branch (gia lap key + embedding that) ---
        import backend.llm as _llm
        orig_key, orig_embed = _llm.has_key, _llm.embed
        try:
            _llm.has_key = lambda: True
            _llm.embed = lambda texts: [[0.0] * 1536 for _ in texts]
            with db.connect() as c:
                vec = "[" + ",".join(["0.0"] * 1536) + "]"
                c.execute("UPDATE chunks SET embedding=%s::vector WHERE doc_id=%s",
                          (vec, doc_a))
            r = cl.post(f"/api/subjects/{sid}/chat",
                        json={"question": "quang hợp"}, headers=H)
            check("chat-vector-branch-hit", r.json()["mode"] == "retrieval_only"
                  and r.json()["sources"]
                  and r.json()["sources"][0]["doc_id"] == doc_a, r.text)
            r = cl.post(f"/api/subjects/{sid}/chat",
                        json={"question": "quang hợp", "doc_id": doc_b}, headers=H)
            check("chat-vector-doc-filter", r.json()["mode"] == "no_context", r.text)
        finally:
            _llm.has_key, _llm.embed = orig_key, orig_embed

    # --- 10. validate helpers (thuan, khong can DB) ---
    check("validate-outline-ok", _validate_outline(
        {"chapters": [{"title": "A", "lessons": ["x", "y"]}]})
        == [{"title": "A", "lessons": ["x", "y"]}])
    check("validate-outline-bad", _validate_outline({"nope": 1}) is None
          and _validate_outline(None) is None
          and _validate_outline({"chapters": [{"title": "A", "lessons": []}]}) is None)
    big = {"chapters": [{"title": f"C{i}", "lessons": [f"L{j}" for j in range(10)]}
                      for i in range(8)]}
    out = _validate_outline(big)
    check("validate-outline-cap", len(out) == 5 and all(len(c["lessons"]) == 6 for c in out))
    chs = _validate_changes([
        {"type": "add_chapter", "title": "X"},
        {"type": "bogus"},
        {"type": "rename_chapter", "chapter_n": "x", "title": "Y"},
        {"type": "rename_chapter", "chapter_n": 2, "title": "Z"},
        {"type": "rename_lesson", "chapter_n": 1, "title": "no-lesson-n"},
    ])
    check("validate-changes-filter", [c["id"] for c in chs] == ["c1", "c4"]
          and chs[0]["type"] == "add_chapter", chs)

    print(f"\nAPI v2: {len(passed)} checks pass")


if __name__ == "__main__":
    try:
        main()
    finally:
        SRV.cleanup()
        shutil.rmtree(TMP, ignore_errors=True)
