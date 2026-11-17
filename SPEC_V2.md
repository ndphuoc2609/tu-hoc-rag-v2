# SPEC v2 — TuHoc RAG (bản đầy đủ, deploy Render)

> Kế thừa SPEC v1 (`~/workspace/tu-hoc-rag/SPEC.md`). Phần không đổi: vấn đề,
> sản phẩm 1 câu, luồng RAG/quiz/chấm tự luận, gamification. File này chỉ ghi
> những gì v2 thêm/đổi. Phương pháp: Superpowers (spec-first) + Ponytail.

## 1. V2 thêm gì so với v1

| V1 | V2 |
|---|---|
| 1 file `app.py`, SQLite, 1 user | `backend/` nhiều module nhỏ, Postgres + pgvector, đa user |
| Chỉ `.txt/.md` | Thêm PDF (`pypdf`), DOCX (`python-docx`) |
| TF-IDF local | Hybrid: vector pgvector + FTS (`to_tsvector`) + TF-IDF fallback |
| Không auth | Register/login, session token DB, role student/teacher |
| Không lớp học | Classes, enrollments, league XP tuần, chấm hàng loạt |
| Chạy local | Docker Compose local + `render.yaml` deploy Render |
| UI inline tạm | Frontend tĩnh của udemi tại `frontend/` (đã xong, serve tại `/`) |

## 2. API contract (KHỚP frontend `frontend/app.js` — đã đọc thật)

Base: backend serve frontend tĩnh tại `/`, API dưới `/api`.
`GET /api/health` → `{ok, model, has_key}` (+ `db`).
Lỗi: JSON `{detail}` + status đúng (400 input sai, 401 chưa login, 404 không thấy).
Frontend live mode luôn gửi Bearer token; chưa login = demo (không gọi API).

- `POST /api/auth/register {name,email,password,role}` → `{token, user}`.
  Password hash `pbkdf2_hmac` stdlib. Token `secrets.token_urlsafe` lưu bảng
  `sessions` dưới dạng sha256. Password < 6 → 400, email trùng → 400.
- `POST /api/auth/login {email,password}` → `{token, user}`.
- `GET /api/me` (auth) → `{id, name, email, role, xp, gems, hearts, streak,
  last_study_date, daily_goal}`. Frontend spread vào `progress`, giữ `xpToday`
  ở client.
- `GET /api/subjects` → `[{id,name,code,desc,progress,lessons}]`.
  `progress` % + `lessons` "x/y bài" tính từ attempts của user; môn seed chung
  cho mọi user. `POST /api/subjects {name}` → `{id,name}` (môn user tự tạo).
- `GET /api/subjects/{id}/chapters` → `[{n,title}]`.
  `GET /api/subjects/{id}/lessons?chapter=1` → `[{n,title,state,note}]`,
  state `done|current|locked` tính từ attempts (mỗi 5 câu đúng mở 1 bài).
  Frontend v2 hiện chưa gọi 2 endpoint này ở live mode (path view vẫn dùng
  demo), nhưng backend vẫn có để bản sau nối.
- `POST /api/subjects/{id}/docs` — cả 2 dạng: (a) multipart `file`
  PDF/DOCX/TXT/MD; (b) JSON `{title, text}` (≥ 20 ký tự).
  → `{id, title, status, chunks}`. File > 20MB → 400. Dedup theo sha256 của
  text đã trích: trùng thì trả doc cũ. Text trích được lưu vào DB (không lưu
  file gốc lên disk — Render filesystem ephemeral).
- `DELETE /api/docs/{id}` → `{ok:true}` (xóa doc + chunks; chỉ owner hoặc
  teacher). `POST /api/docs/{id}/retry` → `{id,status,chunks}` (index lại từ
  text đã lưu; không còn text → 400).
- `POST /api/subjects/{id}/chat {question, mode?, doc_id?}` → `{answer, sources, mode}`,
  sources là list `{text, doc_id, doc_title}`. mode `rag` (mặc định, như cũ:
  `rag_llm|retrieval_only|no_context`) | `general` (không retrieve, Luna temp 0.7;
  không key → `general_unavailable`) | `auto` (có hit → `auto_rag`, không hit →
  `auto_general` với tiền tố "Không có trong tài liệu, đây là câu trả lời chung:").
  `doc_id` lọc retrieval chỉ trong tài liệu đó (doc không thuộc môn → 404).
- `GET /api/subjects/{id}/docs` → `[{id, title, status, chunks, created_at}]`
  (tài liệu đã up của môn, để live mode liệt kê lại sau khi đăng nhập).
- Hybrid path (bảng `path_proposals`, cột `lessons.source_doc_id`):
  `POST /api/subjects {name, level?}` vẫn tạo khung generic 3 chương, có key thì
  Luna sinh dàn ý (cap 5 chương/6 bài) lưu proposal `kind='outline'` pending,
  không key → `outline_proposal: null`.
  `GET /api/subjects/{id}/path/proposal` → proposal pending mới nhất hoặc null.
  `POST /api/subjects/{id}/path/refresh` → proposal `kind='refresh'` từ outline
  hiện tại + tối đa 5 doc (mỗi doc ~1200 ký tự đầu); chưa có doc → 400;
  không key → 503. `POST /api/subjects/{id}/path/proposals/{pid}/apply
  {change_ids}` → duyệt từng change; rỗng → rejected; outline apply THAY khung
  generic cũ (xóa chapters/lessons rồi mới thêm), refresh apply incremental;
  rename UPDATE giữ nguyên id (tiến độ môn tính theo số câu quiz đúng nên không mất).
- `POST /api/subjects/{id}/quiz/generate {n=5}` → `{questions, mode}`.
  Chỉ sinh MCQ. **Không trả `answer_idx` về client** (frontend ép `null`);
  đáp án đúng chỉ nằm ở DB.
- `POST /api/quiz/{qid}/answer {answer_idx}` → `{correct, answer_idx,
  explanation, progress}`. Đúng +10 XP, sai −1 tim (floor 0), ghi attempts +
  reviews (đúng +3 ngày, sai +1 ngày).
- `GET /api/review/due` → `[{id,question,options}]` đến hạn hôm nay của user.
  (Frontend v2 hiện dùng DEMO_DUE ở live mode, backend vẫn có endpoint.)
- `POST /api/subjects/{id}/essay/grade {prompt, rubric, essay}` →
  `{essay_id, scores, total, max_total, overall, mode}`. Tổng tự tính lại từ
  scores. Không key → fallback 60% + ghi rõ chấm tạm. +50 XP.
- `GET /api/classes` → `[{id,name,code,students,xpWeek}]`.
  `POST /api/classes {name}` → `{id,name,code}` (chỉ teacher, code 6 ký tự).
  `GET /api/classes/{id}/league` → `[{name,xp,me}]` theo XP tuần.
  `POST /api/classes/{id}/essays/grade-batch {prompt, rubric}` →
  `{graded, total, average}` (chấm essay pending của lớp; 0 bài chờ → graded 0).
- Seed idempotent lúc startup: 10 môn (Sinh 12, Toán 12, Văn 11, Lý 12, Hóa 12,
  Anh 12, Sử 12, Địa 12, GDCD 12, IELTS/TOEIC). Chương khớp DEMO_CONTENT:
  Sinh 12 = Cơ chế di truyền / Quang hợp / Sinh thái học; Toán 12 = Hàm số /
  Tích phân / Số phức; Văn 11 = Văn học trung đại / Thơ mới / Văn xuôi hiện đại;
  các môn còn lại = Kiến thức nền tảng / Kiến thức trọng tâm / Ôn tập tổng hợp.
  Mỗi chương 5 bài.

## 3. Kiến trúc

```text
tu-hoc-rag-v2/
  backend/
    main.py    # FastAPI app + routes + serve frontend tĩnh
    db.py      # kết nối psycopg, init_db (migration idempotent), seed
    auth.py    # hash password, session token, get_current_user
    rag.py     # chunk, tokenize, trích text PDF/DOCX, retrieval hybrid
    llm.py     # OpenRouter chat + embeddings, extract_json
  frontend/    # udemi đã xong — chỉ patch 3 hàm (deleteDoc/retryDoc/gradeBatch)
  Dockerfile, docker-compose.yml, render.yaml
  requirements.txt, SPEC_V2.md, README.md, .env.example, .gitignore
  tests/test_smoke_v2.py
```

- DB: Postgres 16 + pgvector. `CREATE EXTENSION IF NOT EXISTS vector` lúc
  startup; nếu extension không có (Postgres cũ) → bắt lỗi, log cảnh báo,
  chạy tiếp bằng FTS + TF-IDF, **không crash app**.
- Dùng `psycopg` (binary) + SQL thô, không ORM. Bảng: users, sessions,
  subjects (is_seed, owner_id), chapters, lessons, docs, chunks
  (embedding `vector(1536)`, fts `tsvector`), questions, attempts, reviews,
  essays (status pending|graded, class_id), classes, enrollments, progress.
- RAG: chunk 1000 ký tự overlap 150, giữ tiêu đề chương. Embedding qua
  OpenRouter `POST /api/v1/embeddings`, model `openai/text-embedding-3-small`
  (1536 dims), batch 20 chunk/lần; không key hoặc lỗi → embedding NULL,
  retrieval dùng FTS + TF-IDF. Retrieval hybrid: vector top 5 (cosine `<=>`)
  + FTS top 5, gộp dedup, lấy top 3 cho chat.
- Chat LLM: OpenRouter `POST /api/v1/chat/completions`, model
  `OPENROUTER_MODEL` mặc định `openai/gpt-6-luna`, temp 0.2, timeout 60s,
  lỗi → fallback `retrieval_only`.
- Config: `DATABASE_URL`, `OPENROUTER_API_KEY`, `OPENROUTER_MODEL`.
  `.env` chỉ đọc local, không commit, không dán key vào code/log.

## 4. Render + Docker

- `Dockerfile`: `python:3.12-slim`, `pip install -r requirements.txt`,
  `CMD uvicorn backend.main:app --host 0.0.0.0 --port $PORT`.
- `docker-compose.yml`: `api` (build, port 8000, depends_on db) +
  `db` (`pgvector/pgvector:pg16`, volume `pgdata`, port 5432).
- `render.yaml` (Blueprint): web service runtime docker + database Postgres
  free plan 16. `DATABASE_URL` fromDatabase, `OPENROUTER_API_KEY` sync false.
  App tự chạy `CREATE EXTENSION vector` lúc startup; Render chưa bật thì
  fallback FTS, không crash (ghi trong README).

## 5. Patch frontend (tối thiểu — 3 hàm trong `frontend/app.js`)

- `deleteDoc(id)`: live → `DELETE /api/docs/{id}`, thành công xóa khỏi list
  local + `renderDocs()`; lỗi thì alert lỗi thật.
- `retryDoc(id)`: live → `POST /api/docs/{id}/retry`, cập nhật status/chunks
  từ response rồi `renderDocs()`.
- `gradeBatch()`: live → `POST /api/classes/{classId}/essays/grade-batch`
  với `classId` = lớp đầu tiên trong `DEMO_CLASSES` (lớp đã load từ API khi
  live); hiển thị `{graded, average}` thật; không có lớp → báo rõ.
  Giữ nguyên hành vi demo khi `demoMode`. Sau patch: `node --check app.js`.

## 6. Acceptance v2

1. `POST /api/auth/register` + login → có token; `/api/me` 401 khi không token.
2. Seed 10 môn + chapters đúng DEMO_CONTENT (Sinh/Toán/Văn), mỗi chương 5 bài.
3. Up PDF thật (tạo bằng pypdf) → status done, chunks ≥ 1, dedup up lại
   trùng → trả doc cũ.
4. Chat không key → `retrieval_only`, trả đúng chunk chứa từ khóa, không bịa.
5. Quiz generate → 5 MCQ, không có `answer_idx` trong response; answer đúng
   +10 XP, sai −1 tim; reviews đúng +3 ngày / sai +1 ngày.
6. Essay grade không key → `fallback_tam`, 60%, +50 XP.
7. Classes: teacher tạo lớp → code 6 ký tự; league trả đúng thứ tự XP tuần;
   grade-batch 0 bài chờ → `{graded: 0}` không lỗi.
8. `DELETE /api/docs/{id}` xóa thật; `POST /api/docs/{id}/retry` index lại.
9. `python -m py_compile` mọi file py + `tests/test_smoke_v2.py` pass.
10. Frontend sau patch: `node --check app.js` OK, không đổi hành vi demo.

## 7. Upgrade path (sau v2)

- Ingestion file lớn/chậm → worker queue (Celery/RQ) thay vì xử lý trong request.
- Rerank thật (cross-encoder) thay vì rerank điểm đơn giản.
- Thanh toán Pro, báo cáo phụ huynh, chấm hàng loạt xuất Excel.
