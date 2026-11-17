"""Postgres + pgvector layer. psycopg + SQL tho, khong ORM.

Migration = init_db() idempotent, chay luc startup. Neu CREATE EXTENSION
vector that bai (Postgres cu / chua bat) -> log canh bao, chay tiep bang FTS
+ TF-IDF, KHONG crash app (co HAS_VECTOR).
"""
from __future__ import annotations

import os
from datetime import date, datetime, timedelta
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
for _line in (BASE / ".env").read_text(encoding="utf-8").splitlines() if (BASE / ".env").exists() else []:
    if "=" in _line and not _line.strip().startswith("#"):
        _k, _v = _line.split("=", 1)
        os.environ.setdefault(_k.strip(), _v.strip().strip('"').strip("'"))

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://postgres:postgres@127.0.0.1:5432/tuhoc")

try:
    from zoneinfo import ZoneInfo
    TZ = ZoneInfo("Asia/Ho_Chi_Minh")
except Exception:
    from datetime import timezone
    TZ = timezone(timedelta(hours=7))

HAS_VECTOR = False

SEED_SUBJECTS: list[tuple[str, list[str]]] = [
    ("Sinh 12", ["Cơ chế di truyền", "Quang hợp", "Sinh thái học"]),
    ("Toán 12", ["Hàm số", "Tích phân", "Số phức"]),
    ("Văn 11", ["Văn học trung đại", "Thơ mới", "Văn xuôi hiện đại"]),
    ("Lý 12", ["Kiến thức nền tảng", "Kiến thức trọng tâm", "Ôn tập tổng hợp"]),
    ("Hóa 12", ["Kiến thức nền tảng", "Kiến thức trọng tâm", "Ôn tập tổng hợp"]),
    ("Anh 12", ["Kiến thức nền tảng", "Kiến thức trọng tâm", "Ôn tập tổng hợp"]),
    ("Sử 12", ["Kiến thức nền tảng", "Kiến thức trọng tâm", "Ôn tập tổng hợp"]),
    ("Địa 12", ["Kiến thức nền tảng", "Kiến thức trọng tâm", "Ôn tập tổng hợp"]),
    ("GDCD 12", ["Kiến thức nền tảng", "Kiến thức trọng tâm", "Ôn tập tổng hợp"]),
    ("IELTS/TOEIC", ["Kiến thức nền tảng", "Kiến thức trọng tâm", "Ôn tập tổng hợp"]),
]


def today() -> str:
    return datetime.now(TZ).date().isoformat()


def now_iso() -> str:
    return datetime.now(TZ).isoformat(timespec="seconds")


def connect():
    import psycopg
    from psycopg.rows import dict_row
    return psycopg.connect(DATABASE_URL, row_factory=dict_row, autocommit=True)


def init_db() -> bool:
    """Tao bang + seed. Tra ve HAS_VECTOR. Goi 1 lan luc startup."""
    global HAS_VECTOR
    with connect() as c:
        try:
            c.execute("CREATE EXTENSION IF NOT EXISTS vector")
            HAS_VECTOR = True
        except Exception as e:  # ponytail: Render/Postgres cu chua bat pgvector
            print(f"[db] WARNING: khong bat duoc pgvector ({e}); fallback FTS + TF-IDF")
            HAS_VECTOR = False
        c.execute("""
        CREATE TABLE IF NOT EXISTS users(
            id SERIAL PRIMARY KEY, name TEXT NOT NULL, email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'student',
            created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS sessions(
            token_hash TEXT PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id),
            created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS subjects(
            id SERIAL PRIMARY KEY, name TEXT NOT NULL, is_seed BOOLEAN NOT NULL DEFAULT FALSE,
            owner_id INTEGER REFERENCES users(id), created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS chapters(
            id SERIAL PRIMARY KEY, subject_id INTEGER NOT NULL REFERENCES subjects(id),
            n INTEGER NOT NULL, title TEXT NOT NULL, UNIQUE(subject_id, n));
        CREATE TABLE IF NOT EXISTS lessons(
            id SERIAL PRIMARY KEY, chapter_id INTEGER NOT NULL REFERENCES chapters(id),
            n INTEGER NOT NULL, title TEXT NOT NULL, UNIQUE(chapter_id, n));
        CREATE TABLE IF NOT EXISTS docs(
            id SERIAL PRIMARY KEY, subject_id INTEGER NOT NULL REFERENCES subjects(id),
            owner_id INTEGER REFERENCES users(id), title TEXT NOT NULL, text TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'indexing', chunks INTEGER NOT NULL DEFAULT 0,
            file_hash TEXT, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS chunks(
            id SERIAL PRIMARY KEY, doc_id INTEGER NOT NULL REFERENCES docs(id) ON DELETE CASCADE,
            subject_id INTEGER NOT NULL, text TEXT NOT NULL, ord INTEGER NOT NULL,
            fts TSVECTOR);
        CREATE TABLE IF NOT EXISTS questions(
            id SERIAL PRIMARY KEY, subject_id INTEGER NOT NULL, user_id INTEGER,
            qtype TEXT NOT NULL DEFAULT 'mcq', question TEXT NOT NULL, options JSONB NOT NULL,
            answer_idx INTEGER NOT NULL, explanation TEXT DEFAULT '', source TEXT DEFAULT '',
            created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS attempts(
            id SERIAL PRIMARY KEY, question_id INTEGER NOT NULL, user_id INTEGER NOT NULL,
            correct INTEGER NOT NULL, answered_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS reviews(
            question_id INTEGER NOT NULL, user_id INTEGER NOT NULL,
            next_review TEXT NOT NULL, interval_days INTEGER NOT NULL,
            PRIMARY KEY(question_id, user_id));
        CREATE TABLE IF NOT EXISTS essays(
            id SERIAL PRIMARY KEY, subject_id INTEGER NOT NULL, user_id INTEGER NOT NULL,
            class_id INTEGER, prompt TEXT NOT NULL, rubric JSONB NOT NULL, essay TEXT NOT NULL,
            total REAL, max_total REAL, feedback JSONB, status TEXT NOT NULL DEFAULT 'graded',
            created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS classes(
            id SERIAL PRIMARY KEY, name TEXT NOT NULL, code TEXT UNIQUE NOT NULL,
            teacher_id INTEGER NOT NULL REFERENCES users(id), created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS enrollments(
            class_id INTEGER NOT NULL REFERENCES classes(id), user_id INTEGER NOT NULL REFERENCES users(id),
            PRIMARY KEY(class_id, user_id));
        CREATE TABLE IF NOT EXISTS progress(
            user_id INTEGER PRIMARY KEY REFERENCES users(id), xp INTEGER NOT NULL DEFAULT 0,
            gems INTEGER NOT NULL DEFAULT 0, hearts INTEGER NOT NULL DEFAULT 5,
            streak INTEGER NOT NULL DEFAULT 0, last_study_date TEXT, daily_goal INTEGER NOT NULL DEFAULT 30);
        """)
        if HAS_VECTOR:
            c.execute("ALTER TABLE chunks ADD COLUMN IF NOT EXISTS embedding vector(1536)")
        # --- seed idempotent ---
        for name, chapters in SEED_SUBJECTS:
            row = c.execute("SELECT id FROM subjects WHERE name=%s AND is_seed", (name,)).fetchone()
            if row:
                sid = row["id"]
            else:
                sid = c.execute(
                    "INSERT INTO subjects(name, is_seed, created_at) VALUES(%s, TRUE, %s) RETURNING id",
                    (name, now_iso())).fetchone()["id"]
            for i, ch in enumerate(chapters, start=1):
                title = f"Chương {i}: {ch}"
                chrow = c.execute(
                    "SELECT id FROM chapters WHERE subject_id=%s AND n=%s", (sid, i)).fetchone()
                if chrow:
                    chid = chrow["id"]
                else:
                    chid = c.execute(
                        "INSERT INTO chapters(subject_id, n, title) VALUES(%s,%s,%s) RETURNING id",
                        (sid, i, title)).fetchone()["id"]
                for ln in range(1, 6):
                    c.execute(
                        "INSERT INTO lessons(chapter_id, n, title) VALUES(%s,%s,%s) "
                        "ON CONFLICT (chapter_id, n) DO NOTHING",
                        (chid, ln, f"Bài {ln}"))
    return HAS_VECTOR


# --- progress / gamification (giong v1, nhung theo user) ---
def get_progress(c, user_id: int) -> dict:
    c.execute("INSERT INTO progress(user_id) VALUES(%s) ON CONFLICT (user_id) DO NOTHING", (user_id,))
    row = c.execute("SELECT * FROM progress WHERE user_id=%s", (user_id,)).fetchone()
    return dict(row)


def touch_study(c, user_id: int, xp_gain: int = 0):
    p = get_progress(c, user_id)
    last, t = p["last_study_date"], today()
    if last == t:
        streak = p["streak"] or 1
    elif last == (date.fromisoformat(t) - timedelta(days=1)).isoformat():
        streak = (p["streak"] or 0) + 1
    else:
        streak = 1
    c.execute("UPDATE progress SET xp=xp+%s, streak=%s, last_study_date=%s WHERE user_id=%s",
              (xp_gain, streak, t, user_id))


def xp_week(c, user_id: int) -> int:
    """XP tuan nay: quiz dung +10, essay +50 (tinh tu attempts/essays 7 ngay)."""
    week_ago = (datetime.now(TZ) - timedelta(days=7)).isoformat()
    a = c.execute("SELECT COUNT(*) n FROM attempts WHERE user_id=%s AND correct=1 AND answered_at>=%s",
                  (user_id, week_ago)).fetchone()["n"]
    e = c.execute("SELECT COUNT(*) n FROM essays WHERE user_id=%s AND created_at>=%s",
                  (user_id, week_ago)).fetchone()["n"]
    return a * 10 + e * 50


# --- retrieval hybrid ---
def retrieve_chunks(c, subject_id: int, query: str, k: int = 3):
    """Tra top-k [{id, text, score}]. Vector + FTS, fallback TF-IDF."""
    from . import llm, rag
    merged: dict[int, dict] = {}

    def add(cid, text, score):
        if cid not in merged or score > merged[cid]["score"]:
            merged[cid] = {"id": cid, "text": text, "score": round(float(score), 3)}

    if HAS_VECTOR and llm.has_key():
        vecs = llm.embed([query])
        if vecs and vecs[0]:
            vec_str = "[" + ",".join(str(float(x)) for x in vecs[0]) + "]"
            try:
                for r in c.execute(
                        "SELECT id, text, embedding <=> %s::vector AS dist FROM chunks "
                        "WHERE subject_id=%s AND embedding IS NOT NULL "
                        "ORDER BY dist LIMIT 5", (vec_str, subject_id)):
                    add(r["id"], r["text"], max(0.0, 1.0 - float(r["dist"])))
            except Exception:
                pass
    try:
        for r in c.execute(
                "SELECT id, text, ts_rank(fts, plainto_tsquery('simple', %s)) AS rank FROM chunks "
                "WHERE subject_id=%s AND fts @@ plainto_tsquery('simple', %s) "
                "ORDER BY rank DESC LIMIT 5", (query, subject_id, query)):
            add(r["id"], r["text"], float(r["rank"]))
    except Exception:
        pass
    if merged:
        return sorted(merged.values(), key=lambda x: -x["score"])[:k]
    # fallback TF-IDF trong Python (cap 500 chunk — ponytail ceiling)
    rows = c.execute("SELECT id, text FROM chunks WHERE subject_id=%s ORDER BY ord LIMIT 500",
                     (subject_id,)).fetchall()
    return rag.tfidf_rank([dict(r) for r in rows], query, k=k)
