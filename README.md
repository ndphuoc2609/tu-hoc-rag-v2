# TuHoc RAG v2 — bản đầy đủ

Web tự học: môn học + tài liệu (PDF/DOCX/TXT/MD) + hỏi đáp RAG + quiz +
chấm tự luận theo barem, vỏ gamification kiểu Duolingo. Chi tiết xem `SPEC_V2.md`.
Frontend: udemi đã làm đủ 10 màn hình trong `frontend/`.
Backend: FastAPI + Postgres + pgvector + OpenRouter (Luna `openai/gpt-6-luna`).

## Chạy local bằng Docker Compose

```bash
cp .env.example .env   # điền OPENROUTER_API_KEY vào .env (không dán key vào chat)
docker compose up --build
# mở http://127.0.0.1:8000  (Swagger: /docs)
```

Không có key vẫn chạy được: chat trả về đoạn tài liệu liên quan nhất
(`retrieval_only`), quiz dùng fallback cloze, chấm tự luận ghi rõ "chấm tạm 60%".
Có key thì mới có câu trả lời AI đầy đủ + embedding vector.

## Chạy local không cần Docker (cần Postgres 16 + pgvector chạy sẵn)

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env   # DATABASE_URL trỏ tới Postgres local, điền key
.venv/bin/python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

App tự chạy migration + seed 10 môn lúc startup (`CREATE EXTENSION vector`
nếu được; không được thì log cảnh báo và fallback FTS + TF-IDF, không crash).

## Deploy lên Render (Blueprint)

1. Đẩy code lên GitHub (repo private `ndphuoc2609/tu-hoc-rag-v2`).
2. Render Dashboard → New → Blueprint → chọn repo → Apply.
   `render.yaml` đã khai sẵn: web service (Docker) + Postgres free plan 16.
3. Vào service → Environment → thêm `OPENROUTER_API_KEY` (key thật của bạn),
   giữ `OPENROUTER_MODEL=openai/gpt-6-luna`. `DATABASE_URL` Render tự gắn
   từ database `tuhoc-db`.
4. Deploy xong, mở URL Render cấp → đăng ký tài khoản → dùng.

Lưu ý Render:
- Free web service ngủ sau ~15 phút không có traffic, lần mở đầu sẽ chậm.
- Free Postgres hết hạn sau 90 ngày (Render free) — cần nâng cấp nếu dùng lâu.
- Filesystem của Render là ephemeral: file gốc không được lưu lên disk,
  text trích ra đã lưu vào DB nên không mất dữ liệu khi restart.
- `CREATE EXTENSION vector`: app tự chạy lúc startup. Nếu Render báo lỗi
  quyền, vào Render Postgres → Shell chạy `CREATE EXTENSION vector;`
  rồi redeploy. Nếu vẫn không bật được, app tự fallback FTS, không crash.

## Thử nhanh bằng curl (sau khi đăng ký lấy token)

```bash
curl -s localhost:8000/api/health
curl -s -X POST localhost:8000/api/auth/register -H 'Content-Type: application/json' \
  -d '{"name":"Minh Anh","email":"a@example.com","password":"123456","role":"student"}'
# -> {"token":"...","user":{...}} — dùng token cho các lệnh sau:
export T="TOKEN_O_DAY"
curl -s localhost:8000/api/me -H "Authorization: Bearer $T"
curl -s localhost:8000/api/subjects -H "Authorization: Bearer $T"
curl -s -X POST localhost:8000/api/subjects/1/docs -H "Authorization: Bearer $T" \
  -H 'Content-Type: application/json' \
  -d '{"title":"Quang hợp","text":"Quang hợp là quá trình cây xanh dùng ánh sáng để tổng hợp chất hữu cơ. Quang hợp diễn ra ở lá cây."}'
curl -s -X POST localhost:8000/api/subjects/1/chat -H "Authorization: Bearer $T" \
  -H 'Content-Type: application/json' -d '{"question":"Quang hợp là gì?"}'
```

## Chi phí ước tính (OpenRouter, giá tham khảo)

- Embedding `text-embedding-3-small`: rất rẻ theo số ký tự index (1 cuốn SGK
  ~vài trăm nghìn ký tự ≈ vài xu). Chỉ tốn 1 lần lúc up file.
- Chat/quiz/chấm (Luna): tính theo lượt gọi + token. Hỏi đáp ngắn ~vài trăm
  token/lượt; chấm 1 bài tự luận ~1–2k token. Mức dùng học sinh bình thường
  khoảng vài USD/tháng cho cả lớp nhỏ. Theo dõi usage tại OpenRouter dashboard.

## Kiểm tra logic

```bash
python3 tests/test_smoke_v2.py
```
