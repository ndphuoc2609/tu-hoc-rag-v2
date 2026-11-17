"""TuHoc RAG v2 — FastAPI + Postgres + pgvector + OpenRouter (Luna).

Serve frontend tinh cua udemi tai /, API duoi /api. Khop chinh xac contract
trong SPEC_V2.md (da doc frontend/app.js that).
"""
from __future__ import annotations

import json
import random
import re
import string
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import auth, db, llm, rag

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
MAX_FILE_BYTES = 20 * 1024 * 1024


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        has_vec = db.init_db()
        print(f"[main] DB OK, pgvector={'on' if has_vec else 'off (fallback FTS)'}")
    except Exception as e:
        print(f"[main] WARNING: init_db that bai ({e}); API se tra 500 khi cham DB")
    yield


app = FastAPI(title="TuHoc RAG v2", lifespan=lifespan)


# --- auth dependency ---
def current_user(token: str = Depends(auth.get_token)) -> dict:
    import hashlib
    thash = hashlib.sha256(token.encode()).hexdigest()
    with db.connect() as c:
        row = c.execute(
            "SELECT u.* FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.token_hash=%s",
            (thash,)).fetchone()
    if not row:
        raise HTTPException(401, "phien dang nhap khong hop le")
    return dict(row)


def progress_out(c, user_id: int) -> dict:
    p = db.get_progress(c, user_id)
    return {"xp": p["xp"], "gems": p["gems"], "hearts": p["hearts"],
            "streak": p["streak"], "daily_goal": p["daily_goal"]}


# --- models ---
class RegisterIn(BaseModel):
    name: str
    email: str
    password: str
    role: str = "student"


class LoginIn(BaseModel):
    email: str
    password: str


class SubjectIn(BaseModel):
    name: str


class ChatIn(BaseModel):
    question: str


class QuizGenIn(BaseModel):
    n: int = 5


class AnswerIn(BaseModel):
    answer_idx: int


class DocJsonIn(BaseModel):
    title: str = "Tài liệu"
    text: str


class EssayIn(BaseModel):
    prompt: str
    rubric: object
    essay: str
    class_id: int | None = None


class ClassIn(BaseModel):
    name: str


class BatchIn(BaseModel):
    prompt: str
    rubric: object


def _subject_or_404(c, sid: int, user_id: int | None = None):
    row = c.execute("SELECT * FROM subjects WHERE id=%s", (sid,)).fetchone()
    if not row:
        raise HTTPException(404, "khong co mon hoc")
    return dict(row)


def _login_response(c, user: dict):
    token, thash = auth.new_token()
    c.execute("INSERT INTO sessions(token_hash, user_id, created_at) VALUES(%s,%s,%s)",
              (thash, user["id"], db.now_iso()))
    return {"token": token, "user": auth.public_user(user)}


# --- health / me ---
@app.get("/api/health")
def health():
    try:
        with db.connect() as c:
            c.execute("SELECT 1")
        db_ok = "ok"
    except Exception:
        db_ok = "unavailable"
    return {"ok": True, "model": llm.OPENROUTER_MODEL, "has_key": llm.has_key(), "db": db_ok}


@app.get("/api/me")
def me(user: dict = Depends(current_user)):
    with db.connect() as c:
        p = db.get_progress(c, user["id"])
    return {"id": user["id"], "name": user["name"], "email": user["email"],
            "role": user["role"], **{k: p[k] for k in
            ("xp", "gems", "hearts", "streak", "last_study_date", "daily_goal")}}


# --- auth ---
@app.post("/api/auth/register")
def register(body: RegisterIn):
    if len(body.password) < 6:
        raise HTTPException(400, "mat khau can toi thieu 6 ky tu")
    if body.role not in ("student", "teacher"):
        body.role = "student"
    email = body.email.strip().lower()
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        raise HTTPException(400, "email khong hop le")
    with db.connect() as c:
        if c.execute("SELECT 1 FROM users WHERE email=%s", (email,)).fetchone():
            raise HTTPException(400, "email da duoc dang ky")
        row = c.execute(
            "INSERT INTO users(name, email, password_hash, role, created_at) "
            "VALUES(%s,%s,%s,%s,%s) RETURNING *",
            (body.name.strip() or email.split("@")[0], email,
             auth.hash_password(body.password), body.role, db.now_iso())).fetchone()
        return _login_response(c, dict(row))


@app.post("/api/auth/login")
def login(body: LoginIn):
    with db.connect() as c:
        row = c.execute("SELECT * FROM users WHERE email=%s",
                        (body.email.strip().lower(),)).fetchone()
    if not row or not auth.check_password(body.password, row["password_hash"]):
        raise HTTPException(401, "email hoac mat khau sai")
    with db.connect() as c:
        return _login_response(c, dict(row))


# --- subjects / chapters / lessons ---
def _subject_stats(c, sid: int, user_id: int):
    total_lessons = c.execute(
        "SELECT COUNT(*) n FROM lessons l JOIN chapters ch ON ch.id=l.chapter_id "
        "WHERE ch.subject_id=%s", (sid,)).fetchone()["n"] or 15
    correct = c.execute(
        "SELECT COUNT(*) n FROM attempts a JOIN questions q ON q.id=a.question_id "
        "WHERE q.subject_id=%s AND a.user_id=%s AND a.correct=1",
        (sid, user_id)).fetchone()["n"]
    done = min(total_lessons, correct // 5)
    progress = round(done / total_lessons * 100) if total_lessons else 0
    return done, total_lessons, progress


@app.get("/api/subjects")
def list_subjects(user: dict = Depends(current_user)):
    with db.connect() as c:
        rows = c.execute(
            "SELECT * FROM subjects WHERE is_seed OR owner_id=%s ORDER BY is_seed DESC, id",
            (user["id"],)).fetchall()
        out = []
        for r in rows:
            done, total, prog = _subject_stats(c, r["id"], user["id"])
            out.append({"id": r["id"], "name": r["name"],
                        "code": r["name"][:2], "desc": "",
                        "progress": prog, "lessons": f"{done}/{total} bài"})
        return out


@app.post("/api/subjects")
def create_subject(body: SubjectIn, user: dict = Depends(current_user)):
    if not body.name.strip():
        raise HTTPException(400, "name trong")
    with db.connect() as c:
        row = c.execute(
            "INSERT INTO subjects(name, is_seed, owner_id, created_at) VALUES(%s,FALSE,%s,%s) RETURNING *",
            (body.name.strip(), user["id"], db.now_iso())).fetchone()
        sid = row["id"]
        for i, ch in enumerate(["Kiến thức nền tảng", "Kiến thức trọng tâm", "Ôn tập tổng hợp"], start=1):
            chid = c.execute(
                "INSERT INTO chapters(subject_id, n, title) VALUES(%s,%s,%s) RETURNING id",
                (sid, i, f"Chương {i}: {ch}")).fetchone()["id"]
            for ln in range(1, 6):
                c.execute("INSERT INTO lessons(chapter_id, n, title) VALUES(%s,%s,%s)",
                          (chid, ln, f"Bài {ln}"))
    return {"id": sid, "name": body.name.strip()}


@app.get("/api/subjects/{sid}/chapters")
def list_chapters(sid: int, user: dict = Depends(current_user)):
    with db.connect() as c:
        _subject_or_404(c, sid)
        rows = c.execute("SELECT n, title FROM chapters WHERE subject_id=%s ORDER BY n", (sid,)).fetchall()
    return [{"n": r["n"], "title": r["title"]} for r in rows]


@app.get("/api/subjects/{sid}/lessons")
def list_lessons(sid: int, chapter: int = 1, user: dict = Depends(current_user)):
    with db.connect() as c:
        _subject_or_404(c, sid)
        done, _, _ = _subject_stats(c, sid, user["id"])
        ch = c.execute("SELECT id FROM chapters WHERE subject_id=%s AND n=%s", (sid, chapter)).fetchone()
        if not ch:
            raise HTTPException(404, "khong co chuong")
        rows = c.execute("SELECT n, title FROM lessons WHERE chapter_id=%s ORDER BY n", (ch["id"],)).fetchall()
        base = (chapter - 1) * 5  # so bai toan cuc trong mon (mo khoa tuan tu)
        out = []
        for r in rows:
            n = base + r["n"]
            if n <= done:
                state, note = "done", "Đã xong · 50 XP"
            elif n == done + 1:
                state, note = "current", "Đang học · 5 câu"
            elif r["n"] == 1:
                state, note = "locked", "Mở sau khi xong chương trước"
            else:
                state, note = "locked", f"Mở sau khi xong Bài {r['n'] - 1}"
            out.append({"n": r["n"], "title": r["title"], "state": state, "note": note})
        return out


# --- docs ---
def _index_text(c, sid: int, owner_id: int, title: str, text: str) -> dict:
    """Chia chunk + insert + embed (neu co key). Tra {id, title, status, chunks}."""
    import hashlib
    fhash = hashlib.sha256(text.encode("utf-8")).hexdigest()
    dup = c.execute("SELECT id, title, status, chunks FROM docs WHERE subject_id=%s AND file_hash=%s",
                    (sid, fhash)).fetchone()
    if dup:
        return {"id": dup["id"], "title": dup["title"], "status": dup["status"],
                "chunks": dup["chunks"], "dedup": True}
    chunks = rag.chunk_text(text)
    doc = c.execute(
        "INSERT INTO docs(subject_id, owner_id, title, text, status, chunks, file_hash, created_at) "
        "VALUES(%s,%s,%s,%s,'indexing',0,%s,%s) RETURNING id",
        (sid, owner_id, title, text, fhash, db.now_iso())).fetchone()
    did = doc["id"]
    chunk_ids = []
    for i, ch in enumerate(chunks):
        row = c.execute(
            "INSERT INTO chunks(doc_id, subject_id, text, ord, fts) "
            "VALUES(%s,%s,%s,%s,to_tsvector('simple', %s)) RETURNING id",
            (did, sid, ch, i, ch)).fetchone()
        chunk_ids.append((row["id"], ch))
    if db.HAS_VECTOR and llm.has_key():
        # ponytail: embed dong bo trong request; file <=20MB thi du nhanh.
        # Upgrade path: day sang worker queue khi file lon / nhieu.
        for j in range(0, len(chunk_ids), 20):
            batch = chunk_ids[j:j + 20]
            vecs = llm.embed([t for _, t in batch])
            for (cid, _), vec in zip(batch, vecs):
                if vec:
                    vstr = "[" + ",".join(str(float(x)) for x in vec) + "]"
                    try:
                        c.execute("UPDATE chunks SET embedding=%s::vector WHERE id=%s", (vstr, cid))
                    except Exception:
                        pass
    c.execute("UPDATE docs SET status='done', chunks=%s WHERE id=%s", (len(chunks), did))
    return {"id": did, "title": title, "status": "done", "chunks": len(chunks)}


@app.post("/api/subjects/{sid}/docs")
async def add_doc(sid: int, request: Request, user: dict = Depends(current_user)):
    ctype = request.headers.get("content-type", "")
    with db.connect() as c:
        _subject_or_404(c, sid)
        if "multipart/form-data" in ctype:
            form = await request.form()
            up = form.get("file")
            if up is None:
                raise HTTPException(400, "thieu file")
            data = await up.read()
            if len(data) > MAX_FILE_BYTES:
                raise HTTPException(400, "file vuot qua 20MB")
            try:
                text = rag.extract_text(up.filename or "file", data)
            except Exception as e:
                raise HTTPException(400, f"khong doc duoc file: {e}")
            title = up.filename or "Tài liệu"
        else:
            try:
                body = await request.json()
            except Exception:
                raise HTTPException(400, "body phai la JSON {title, text} hoac multipart file")
            text, title = (body.get("text") or ""), (body.get("title") or "Tài liệu")
        if len(text.strip()) < 20:
            raise HTTPException(400, "text qua ngan (can >= 20 ky tu)")
        try:
            return _index_text(c, sid, user["id"], title, text)
        except Exception as e:
            # luu lai doc loi de retry duoc (khong mat text)
            try:
                c.execute("INSERT INTO docs(subject_id, owner_id, title, text, status, chunks, created_at) "
                          "VALUES(%s,%s,%s,%s,'error',0,%s)",
                          (sid, user["id"], title, text, db.now_iso()))
            except Exception:
                pass
            raise HTTPException(400, f"lap chi muc that bai: {e}")


@app.delete("/api/docs/{did}")
def delete_doc(did: int, user: dict = Depends(current_user)):
    with db.connect() as c:
        row = c.execute("SELECT * FROM docs WHERE id=%s", (did,)).fetchone()
        if not row:
            raise HTTPException(404, "khong co tai lieu")
        if row["owner_id"] != user["id"] and user["role"] != "teacher":
            raise HTTPException(403, "khong co quyen xoa tai lieu nay")
        c.execute("DELETE FROM docs WHERE id=%s", (did,))
    return {"ok": True}


@app.post("/api/docs/{did}/retry")
def retry_doc(did: int, user: dict = Depends(current_user)):
    with db.connect() as c:
        row = c.execute("SELECT * FROM docs WHERE id=%s", (did,)).fetchone()
        if not row:
            raise HTTPException(404, "khong co tai lieu")
        if row["owner_id"] != user["id"] and user["role"] != "teacher":
            raise HTTPException(403, "khong co quyen")
        if not (row["text"] or "").strip():
            raise HTTPException(400, "khong con text goc de index lai")
        c.execute("DELETE FROM chunks WHERE doc_id=%s", (did,))
        c.execute("UPDATE docs SET status='indexing', chunks=0 WHERE id=%s", (did,))
        chunks = rag.chunk_text(row["text"])
        for i, ch in enumerate(chunks):
            c.execute("INSERT INTO chunks(doc_id, subject_id, text, ord, fts) "
                      "VALUES(%s,%s,%s,%s,to_tsvector('simple', %s))",
                      (did, row["subject_id"], ch, i, ch))
        c.execute("UPDATE docs SET status='done', chunks=%s WHERE id=%s", (len(chunks), did))
    return {"id": did, "status": "done", "chunks": len(chunks)}


# --- chat RAG ---
@app.post("/api/subjects/{sid}/chat")
def chat(sid: int, body: ChatIn, user: dict = Depends(current_user)):
    with db.connect() as c:
        _subject_or_404(c, sid)
        hits = db.retrieve_chunks(c, sid, body.question, k=3)
        if not hits:
            return {"answer": "Chưa có tài liệu nào khớp câu hỏi này trong môn học. Hãy up thêm tài liệu rồi hỏi lại.",
                    "sources": [], "mode": "no_context"}
        ctx = "\n---\n".join(h["text"] for h in hits)
        content = llm.chat([
            {"role": "system", "content": "Bạn là trợ lý học tập tiếng Việt. Chỉ trả lời từ NGỮ CẢNH dưới đây, trích nguồn là đoạn nào. Không có trong ngữ cảnh thì nói rõ 'không có trong tài liệu', không bịa."},
            {"role": "user", "content": f"NGỮ CẢNH:\n{ctx}\n\nCÂU HỎI: {body.question}"}])
        db.touch_study(c, user["id"], xp_gain=5)
        if content is None:
            return {"answer": "Chưa gắn key OpenRouter nên chưa có câu trả lời AI. Đây là đoạn liên quan nhất trong tài liệu của bạn:",
                    "sources": hits, "mode": "retrieval_only"}
        return {"answer": content, "sources": hits, "mode": "rag_llm"}


# --- quiz ---
@app.post("/api/subjects/{sid}/quiz/generate")
def quiz_generate(sid: int, body: QuizGenIn, user: dict = Depends(current_user)):
    n = max(1, min(body.n, 10))
    with db.connect() as c:
        _subject_or_404(c, sid)
        hits = db.retrieve_chunks(c, sid, "khái niệm định nghĩa ví dụ", k=3)
        ctx = "\n".join(h["text"] for h in hits)
        items, mode = [], "fallback"
        content = llm.chat([
            {"role": "system", "content": "Chỉ trả JSON list, không giải thích. Mỗi phần tử: {question, options (4 chuỗi), answer_idx (0-3), explanation, source}."},
            {"role": "user", "content": f"Tạo {n} câu trắc nghiệm từ tài liệu sau, đáp án nhiễu phải gần đúng:\n{ctx}"}],
            temperature=0.4, max_tokens=2000) if ctx else None
        parsed = llm.extract_json(content) if content else None
        if isinstance(parsed, list) and parsed and all(
                isinstance(x, dict) and len(x.get("options", [])) == 4 for x in parsed):
            items, mode = parsed[:n], "llm"
        else:
            rows = c.execute("SELECT id, text FROM chunks WHERE subject_id=%s ORDER BY ord",
                             (sid,)).fetchall()
            items = rag.fallback_quiz([dict(r) for r in rows], n)
        if not items:
            raise HTTPException(400, "chua co tai lieu de tao quiz")
        out = []
        for it in items:
            row = c.execute(
                "INSERT INTO questions(subject_id, user_id, qtype, question, options, answer_idx, explanation, source, created_at) "
                "VALUES(%s,%s,'mcq',%s,%s,%s,%s,%s,%s) RETURNING id",
                (sid, user["id"], it["question"], json.dumps(it["options"], ensure_ascii=False),
                 int(it["answer_idx"]), it.get("explanation", ""), (it.get("source") or "")[:500],
                 db.now_iso())).fetchone()
            # KHONG tra answer_idx ve client — frontend ep null, dap an chi nam o DB.
            out.append({"id": row["id"], "question": it["question"],
                        "options": it["options"], "source": (it.get("source") or "")[:200],
                        "explanation": it.get("explanation", "")})
    return {"questions": out, "mode": mode}


@app.post("/api/quiz/{qid}/answer")
def quiz_answer(qid: int, body: AnswerIn, user: dict = Depends(current_user)):
    with db.connect() as c:
        q = c.execute("SELECT * FROM questions WHERE id=%s", (qid,)).fetchone()
        if not q:
            raise HTTPException(404, "khong co cau hoi")
        correct = int(body.answer_idx == q["answer_idx"])
        c.execute("INSERT INTO attempts(question_id, user_id, correct, answered_at) VALUES(%s,%s,%s,%s)",
                  (qid, user["id"], correct, db.now_iso()))
        from datetime import date, timedelta
        interval = 3 if correct else 1
        nxt = (date.fromisoformat(db.today()) + timedelta(days=interval)).isoformat()
        c.execute("INSERT INTO reviews(question_id, user_id, next_review, interval_days) VALUES(%s,%s,%s,%s) "
                  "ON CONFLICT (question_id, user_id) DO UPDATE SET next_review=EXCLUDED.next_review, interval_days=EXCLUDED.interval_days",
                  (qid, user["id"], nxt, interval))
        if correct:
            db.touch_study(c, user["id"], xp_gain=10)
            last5 = c.execute(
                "SELECT correct FROM attempts WHERE user_id=%s ORDER BY id DESC LIMIT 5",
                (user["id"],)).fetchall()
            if len(last5) == 5 and all(r["correct"] == 1 for r in last5):
                c.execute("UPDATE progress SET gems=gems+5 WHERE user_id=%s", (user["id"],))
        else:
            c.execute("UPDATE progress SET hearts=GREATEST(hearts-1,0) WHERE user_id=%s", (user["id"],))
            db.touch_study(c, user["id"], xp_gain=0)
        prog = progress_out(c, user["id"])
    return {"correct": bool(correct), "answer_idx": q["answer_idx"],
            "explanation": q["explanation"], "progress": prog}


@app.get("/api/review/due")
def review_due(user: dict = Depends(current_user)):
    with db.connect() as c:
        rows = c.execute(
            "SELECT q.id, q.question, q.options FROM reviews r JOIN questions q ON q.id=r.question_id "
            "WHERE r.user_id=%s AND r.next_review<=%s ORDER BY r.next_review LIMIT 20",
            (user["id"], db.today())).fetchall()
    return [{"id": r["id"], "question": r["question"], "options": r["options"]} for r in rows]


# --- essay ---
def _grade_essay_scores(prompt: str, rubric: list, essay: str):
    """Tra (scores, total, overall, mode). Dung chung cho grade + grade-batch."""
    max_total = sum(r["max"] for r in rubric)
    content = llm.chat([
        {"role": "system", "content": "Bạn là giáo viên chấm tự luận. Chỉ trả JSON, không giải thích: {scores:[{criterion, score, max, quote, feedback}], total, max_total, overall}. Trích quote đúng câu trong bài làm. Chấm chặt theo barem."},
        {"role": "user", "content": f"ĐỀ: {prompt}\nBAREM: {json.dumps(rubric, ensure_ascii=False)}\nBÀI LÀM:\n{essay}"}],
        temperature=0.1, max_tokens=1500)
    parsed = llm.extract_json(content) if content else None
    if isinstance(parsed, dict) and isinstance(parsed.get("scores"), list) and parsed["scores"]:
        scores = []
        for s, r in zip(parsed["scores"], rubric):
            scores.append({"criterion": s.get("criterion", r["criterion"]),
                           "score": float(s.get("score", 0)), "max": r["max"],
                           "quote": (s.get("quote") or "")[:300], "feedback": s.get("feedback", "")})
        return scores, sum(s["score"] for s in scores), parsed.get("overall", ""), "llm"
    scores = [{"criterion": r["criterion"], "score": round(r["max"] * 0.6, 1), "max": r["max"],
               "quote": "", "feedback": "Chấm tạm (chưa có key OpenRouter). Gắn key để chấm thật theo barem."}
              for r in rubric]
    return scores, sum(s["score"] for s in scores), "Chấm tạm 60% — cần key để chấm thật.", "fallback_tam"


@app.post("/api/subjects/{sid}/essay/grade")
def essay_grade(sid: int, body: EssayIn, user: dict = Depends(current_user)):
    rubric = rag.parse_rubric(body.rubric)
    max_total = sum(r["max"] for r in rubric)
    scores, total, overall, mode = _grade_essay_scores(body.prompt, rubric, body.essay)
    with db.connect() as c:
        _subject_or_404(c, sid)
        db.touch_study(c, user["id"], xp_gain=50)
        row = c.execute(
            "INSERT INTO essays(subject_id, user_id, class_id, prompt, rubric, essay, total, max_total, feedback, status, created_at) "
            "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,'graded',%s) RETURNING id",
            (sid, user["id"], body.class_id, body.prompt, json.dumps(rubric, ensure_ascii=False),
             body.essay, total, max_total,
             json.dumps({"scores": scores, "overall": overall}, ensure_ascii=False), db.now_iso())).fetchone()
    return {"essay_id": row["id"], "scores": scores, "total": total,
            "max_total": max_total, "overall": overall, "mode": mode}


# --- classes ---
def _class_members(c, class_id: int):
    rows = c.execute(
        "SELECT u.* FROM enrollments e JOIN users u ON u.id=e.user_id WHERE e.class_id=%s",
        (class_id,)).fetchall()
    return [dict(r) for r in rows]


@app.get("/api/classes")
def list_classes(user: dict = Depends(current_user)):
    with db.connect() as c:
        rows = c.execute(
            "SELECT cl.* FROM classes cl WHERE cl.teacher_id=%s "
            "OR EXISTS (SELECT 1 FROM enrollments e WHERE e.class_id=cl.id AND e.user_id=%s) "
            "ORDER BY cl.id", (user["id"], user["id"])).fetchall()
        out = []
        for r in rows:
            members = _class_members(c, r["id"])
            xp_week = sum(db.xp_week(c, m["id"]) for m in members)
            out.append({"id": r["id"], "name": r["name"], "code": r["code"],
                        "students": len(members), "xpWeek": xp_week})
        return out


@app.post("/api/classes")
def create_class(body: ClassIn, user: dict = Depends(current_user)):
    if user["role"] != "teacher":
        raise HTTPException(403, "chi giao vien moi tao lop")
    if not body.name.strip():
        raise HTTPException(400, "name trong")
    code = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
    with db.connect() as c:
        row = c.execute(
            "INSERT INTO classes(name, code, teacher_id, created_at) VALUES(%s,%s,%s,%s) RETURNING *",
            (body.name.strip(), code, user["id"], db.now_iso())).fetchone()
        c.execute("INSERT INTO enrollments(class_id, user_id) VALUES(%s,%s) ON CONFLICT DO NOTHING",
                  (row["id"], user["id"]))
    return {"id": row["id"], "name": row["name"], "code": row["code"]}


@app.get("/api/classes/{cid}/league")
def class_league(cid: int, user: dict = Depends(current_user)):
    with db.connect() as c:
        if not c.execute("SELECT 1 FROM classes WHERE id=%s", (cid,)).fetchone():
            raise HTTPException(404, "khong co lop")
        members = _class_members(c, cid)
        board = [{"name": m["name"], "xp": db.xp_week(c, m["id"]), "me": m["id"] == user["id"]}
                 for m in members]
    return sorted(board, key=lambda x: -x["xp"])


@app.post("/api/classes/{cid}/essays/grade-batch")
def grade_batch(cid: int, body: BatchIn, user: dict = Depends(current_user)):
    if user["role"] != "teacher":
        raise HTTPException(403, "chi giao vien moi cham hang loat")
    rubric = rag.parse_rubric(body.rubric)
    with db.connect() as c:
        if not c.execute("SELECT 1 FROM classes WHERE id=%s AND teacher_id=%s", (cid, user["id"])).fetchone():
            raise HTTPException(404, "khong co lop hoac khong phai lop cua ban")
        pending = c.execute(
            "SELECT e.* FROM essays e JOIN enrollments en ON en.user_id=e.user_id "
            "WHERE en.class_id=%s AND e.status='pending'", (cid,)).fetchall()
        graded, total = 0, 0.0
        for e in pending:
            scores, tot, overall, _mode = _grade_essay_scores(body.prompt, rubric, e["essay"])
            max_total = sum(r["max"] for r in rubric)
            c.execute("UPDATE essays SET total=%s, max_total=%s, feedback=%s, status='graded' WHERE id=%s",
                      (tot, max_total, json.dumps({"scores": scores, "overall": overall}, ensure_ascii=False), e["id"]))
            graded, total = graded + 1, total + tot
    return {"graded": graded, "total": len(pending),
            "average": round(total / graded, 2) if graded else 0}


# --- static frontend (serve CUOI CUNG — API uu tien truoc) ---
app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")


if __name__ == "__main__":
    import os
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "8000")))
