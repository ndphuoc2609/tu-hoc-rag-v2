/* TuHoc RAG v2 — frontend logic.
   API contract v2 (FastAPI, prefix /api) — khong tu bia endpoint.
   Neu backend chua chay: che do demo, banner ghi ro, du lieu mau trong file nay.
   Token luu localStorage, gui kem Bearer. Khong bao gio hien key. */
"use strict";

/* ---------- API client ---------- */
const API_BASE = (location.port === "8000" || location.hostname === "127.0.0.1")
  ? "" : "http://127.0.0.1:8000";
const $ = (s, r) => (r || document).querySelector(s);
const $$ = (s, r) => Array.from((r || document).querySelectorAll(s));
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));

let token = localStorage.getItem("tuhoc_token") || "";
let role = localStorage.getItem("tuhoc_role") || "student";
let userName = localStorage.getItem("tuhoc_name") || "Minh Anh";
let demoMode = !token;           // chua dang nhap = demo
let apiLive = false;

async function api(path, opts) {
  const res = await fetch(API_BASE + "/api" + path, {
    headers: Object.assign({"Content-Type": "application/json"},
      token ? {Authorization: "Bearer " + token} : {}),
    ...opts,
  });
  const text = await res.text();
  let data = null;
  try { data = JSON.parse(text); } catch (e) { data = {detail: text}; }
  if (!res.ok) throw new Error(typeof data?.detail === "string" ? data.detail : (data?.detail ? JSON.stringify(data.detail) : ("Lỗi " + res.status)));
  return data;
}
async function apiForm(path, formData) {
  const res = await fetch(API_BASE + "/api" + path, {
    method: "POST",
    headers: token ? {Authorization: "Bearer " + token} : {},
    body: formData,
  });
  if (!res.ok) throw new Error("Tải lên thất bại (" + res.status + ")");
  return res.json();
}
async function checkHealth() {
  try { const h = await api("/health"); apiLive = !!h.ok; }
  catch (e) { apiLive = false; }
  demoMode = !apiLive || !token;
  $("#demoBanner").hidden = !demoMode;
}

/* ---------- Demo data (ghi ro la mau) ---------- */
const DEMO_SUBJECTS = [
  {id: 1, name: "Sinh 12", code: "Si", desc: "Di truyền, tiến hóa, sinh thái", progress: 40, lessons: "8/20 bài"},
  {id: 2, name: "Toán 12", code: "To", desc: "Hàm số, tích phân, số phức", progress: 45, lessons: "9/20 bài"},
  {id: 3, name: "Văn 11", code: "Vă", desc: "Văn học trung đại và hiện đại", progress: 30, lessons: "6/20 bài"},
  {id: 4, name: "Lý 12", code: "Lý", desc: "Dao động, sóng, điện xoay chiều", progress: 20, lessons: "4/20 bài"},
  {id: 5, name: "Hóa 12", code: "Hó", desc: "Este, kim loại, polime", progress: 15, lessons: "3/20 bài"},
  {id: 6, name: "Anh 12", code: "An", desc: "Ngữ pháp, từ vựng, đọc hiểu", progress: 55, lessons: "11/20 bài"},
  {id: 7, name: "Sử 12", code: "Sử", desc: "Lịch sử Việt Nam hiện đại", progress: 40, lessons: "8/20 bài"},
  {id: 8, name: "Địa 12", code: "Đị", desc: "Địa lí tự nhiên và kinh tế", progress: 25, lessons: "5/20 bài"},
  {id: 9, name: "GDCD 12", code: "GD", desc: "Pháp luật và công dân", progress: 70, lessons: "14/20 bài"},
  {id: 10, name: "IELTS / TOEIC", code: "IE", desc: "Luyện thi tiếng Anh quốc tế", progress: 35, lessons: "7/20 bài"},
];
/* Du lieu mau THEO MON (H1): chi Sinh/Toan/Van co du lieu mau day du.
   Mon khac tra null -> UI hien empty state "chua co bai hoc", khong nhet bai Sinh 12 vao. */
const DEMO_CONTENT = {
  1: {
    chapters: ["Chương 1: Cơ chế di truyền", "Chương 2: Quang hợp", "Chương 3: Sinh thái học"],
    lessons: [
      {n: 1, title: "Bài 1: Khái niệm quang hợp", state: "done", note: "Đã xong · 50 XP"},
      {n: 2, title: "Bài 2: Pha sáng", state: "done", note: "Đã xong · 50 XP"},
      {n: 3, title: "Bài 3: Pha tối", state: "current", note: "Đang học · 5 câu"},
      {n: 4, title: "Bài 4: Các yếu tố ảnh hưởng", state: "locked", note: "Mở sau khi xong Bài 3"},
      {n: 5, title: "Bài 5: Ôn tập chương", state: "locked", note: "Mở sau khi xong Bài 4"},
    ],
    quiz: [
      {id: 101, qtype: "mcq", question: "Quang hợp diễn ra chủ yếu ở bộ phận nào của cây?", options: ["Rễ cây", "Lá cây", "Thân cây", "Hoa"], answer_idx: 1, explanation: "Quang hợp diễn ra ở lá, trong lục lạp của tế bào lá.", source: "Sinh học 12, Chương 2 — Quang hợp, trang 42."},
      {id: 102, qtype: "tf", question: "Pha sáng của quang hợp cần ánh sáng mặt trời trực tiếp.", options: ["Đúng", "Sai"], answer_idx: 0, explanation: "Đúng. Pha sáng dùng năng lượng ánh sáng để tạo ATP và NADPH.", source: "Sinh học 12, Chương 2, trang 44."},
      {id: 103, qtype: "mcq", question: "Sản phẩm chính của pha tối là gì?", options: ["Oxi", "ATP", "Chất hữu cơ (glucôzơ)", "Nước"], answer_idx: 2, explanation: "Pha tối dùng ATP và NADPH từ pha sáng để tổng hợp chất hữu cơ.", source: "Sinh học 12, Chương 2, trang 46."},
      {id: 104, qtype: "fill", question: "Quang hợp giải phóng khí ______ ra môi trường.", options: [], answer_text: "oxi", answer_alt: ["o2", "khí oxi", "oxygen"], explanation: "Cây thải oxi ra ngoài trong quá trình quang hợp.", source: "Sinh học 12, Chương 2, trang 42."},
      {id: 105, qtype: "mcq", question: "Yếu tố nào sau đây KHÔNG ảnh hưởng trực tiếp tới quang hợp?", options: ["Cường độ ánh sáng", "Nồng độ khí cacbonic", "Màu sắc của chậu cây", "Nhiệt độ"], answer_idx: 2, explanation: "Màu chậu không ảnh hưởng tới quang hợp; ánh sáng, CO₂ và nhiệt độ thì có.", source: "Sinh học 12, Chương 2, trang 48."},
    ],
    chat: [
      {keys: ["pha sáng", "pha tối"], answer: "Pha sáng cần ánh sáng mặt trời, diễn ra ở màng tilacôit và tạo ATP, NADPH. Pha tối diễn ra ở chất nền lục lạp, không cần ánh sáng trực tiếp, dùng ATP và NADPH để tổng hợp chất hữu cơ.", sources: ["Sinh học 12, Chương 2, trang 44: pha sáng tạo ATP và NADPH.", "Trang 46: pha tối tổng hợp chất hữu cơ."]},
      {keys: ["ví dụ"], answer: "Ví dụ: cây lúa quang hợp tạo tinh bột trong hạt gạo; rừng cây hấp thụ khí cacbonic và thải oxi, giúp cân bằng không khí.", sources: ["Sinh học 12, Chương 2, trang 48: vai trò của quang hợp với môi trường."]},
      {keys: [], answer: "Quang hợp là quá trình cây xanh dùng năng lượng ánh sáng để tổng hợp chất hữu cơ từ nước và khí cacbonic. Quá trình diễn ra ở lá, trong lục lạp, gồm pha sáng và pha tối.", sources: ["Sinh học 12, Chương 2 — Quang hợp, trang 42: “Quang hợp là quá trình cây xanh dùng ánh sáng để tổng hợp chất hữu cơ.”"]},
    ],
  },
  2: {
    chapters: ["Chương 1: Hàm số", "Chương 2: Tích phân", "Chương 3: Số phức"],
    lessons: [
      {n: 1, title: "Bài 1: Khái niệm đạo hàm", state: "done", note: "Đã xong · 50 XP"},
      {n: 2, title: "Bài 2: Quy tắc tính đạo hàm", state: "done", note: "Đã xong · 50 XP"},
      {n: 3, title: "Bài 3: Tích phân", state: "current", note: "Đang học · 5 câu"},
      {n: 4, title: "Bài 4: Số phức", state: "locked", note: "Mở sau khi xong Bài 3"},
      {n: 5, title: "Bài 5: Ôn tập chương", state: "locked", note: "Mở sau khi xong Bài 4"},
    ],
    quiz: [
      {id: 201, qtype: "mcq", question: "Đạo hàm của hàm số f(x) = x² là?", options: ["2x", "x", "2", "x²"], answer_idx: 0, explanation: "Đạo hàm của x² là 2x theo quy tắc đạo hàm hàm lũy thừa.", source: "Toán 12, Chương 1 — Đạo hàm, trang 18."},
      {id: 202, qtype: "mcq", question: "Nguyên hàm của 2x là?", options: ["x² + C", "2x² + C", "x + C", "2 + C"], answer_idx: 0, explanation: "Nguyên hàm của 2x là x² + C, vì đạo hàm của x² là 2x.", source: "Toán 12, Chương 2 — Tích phân, trang 52."},
      {id: 203, qtype: "tf", question: "Tích phân từ 0 đến 1 của 2x dx bằng 1.", options: ["Đúng", "Sai"], answer_idx: 0, explanation: "Đúng. ∫₀¹ 2x dx = [x²]₀¹ = 1.", source: "Toán 12, Chương 2, trang 54."},
      {id: 204, qtype: "fill", question: "Số phức z = 3 + 4i có mô-đun bằng ______.", options: [], answer_text: "5", answer_alt: ["5.0"], explanation: "Mô-đun |z| = √(3² + 4²) = 5.", source: "Toán 12, Chương 3 — Số phức, trang 71."},
      {id: 205, qtype: "mcq", question: "Hàm số y = x³ đồng biến trên khoảng nào?", options: ["(0; +∞)", "R", "(-∞; 0)", "Không đồng biến"], answer_idx: 1, explanation: "y' = 3x² ≥ 0 với mọi x nên hàm đồng biến trên R.", source: "Toán 12, Chương 1, trang 12."},
    ],
    chat: [
      {keys: ["đạo hàm"], answer: "Đạo hàm f'(x) đo tốc độ thay đổi tức thời của hàm số tại x. Ví dụ: f(x) = x² thì f'(x) = 2x.", sources: ["Toán 12, Chương 1 — Đạo hàm, trang 18."]},
      {keys: ["tích phân"], answer: "Tích phân dùng để tính diện tích hình phẳng và thể tích. Ví dụ: ∫₀¹ 2x dx = 1.", sources: ["Toán 12, Chương 2 — Tích phân, trang 54."]},
      {keys: [], answer: "Hỏi mình về đạo hàm, tích phân hoặc số phức trong tài liệu Toán 12 nhé. Ví dụ: “Đạo hàm của x² là gì?”", sources: ["Toán 12, Chương 1–3."]},
    ],
  },
  3: {
    chapters: ["Chương 1: Văn học trung đại", "Chương 2: Thơ mới", "Chương 3: Văn xuôi hiện đại"],
    lessons: [
      {n: 1, title: "Bài 1: Thơ mới là gì", state: "done", note: "Đã xong · 50 XP"},
      {n: 2, title: "Bài 2: Tràng giang", state: "done", note: "Đã xong · 50 XP"},
      {n: 3, title: "Bài 3: Đây thôn Vĩ Dạ", state: "current", note: "Đang học · 5 câu"},
      {n: 4, title: "Bài 4: Vội vàng", state: "locked", note: "Mở sau khi xong Bài 3"},
      {n: 5, title: "Bài 5: Ôn tập chương", state: "locked", note: "Mở sau khi xong Bài 4"},
    ],
    quiz: [
      {id: 301, qtype: "mcq", question: "Tác giả bài thơ “Tràng giang” là ai?", options: ["Huy Cận", "Xuân Diệu", "Hàn Mặc Tử", "Chế Lan Viên"], answer_idx: 0, explanation: "“Tràng giang” là bài thơ nổi tiếng của Huy Cận, in trong tập Lửa thiêng (1940).", source: "Văn 11, Chương 2 — Thơ mới, trang 30."},
      {id: 302, qtype: "tf", question: "“Tràng giang” được viết theo thể thơ bảy chữ.", options: ["Đúng", "Sai"], answer_idx: 0, explanation: "Đúng. Bài thơ viết theo thể thất ngôn, gồm 4 khổ, mỗi khổ 4 câu bảy chữ.", source: "Văn 11, Chương 2, trang 31."},
      {id: 303, qtype: "mcq", question: "Hình ảnh “củi một cành khô lạc mấy dòng” gợi cảm giác gì?", options: ["Cô đơn, trôi dạt", "Vui tươi, rộn ràng", "Hùng vĩ, tráng lệ", "Bình yên, no ấm"], answer_idx: 0, explanation: "Cành củi khô trôi dạt giữa dòng sông rộng gợi nỗi cô đơn của con người trước vũ trụ bao la.", source: "Văn 11, Chương 2, trang 32."},
      {id: 304, qtype: "fill", question: "“Tràng giang” in trong tập thơ ______ của Huy Cận.", options: [], answer_text: "Lửa thiêng", answer_alt: ["lua thieng"], explanation: "Tập thơ Lửa thiêng xuất bản năm 1940.", source: "Văn 11, Chương 2, trang 30."},
      {id: 305, qtype: "mcq", question: "Phong trào Thơ mới nở rộ vào giai đoạn nào?", options: ["1930–1945", "1945–1954", "1900–1920", "1975–1986"], answer_idx: 0, explanation: "Phong trào Thơ mới nở rộ trong giai đoạn 1930–1945.", source: "Văn 11, Chương 2, trang 28."},
    ],
    chat: [
      {keys: ["tràng giang"], answer: "“Tràng giang” của Huy Cận (tập Lửa thiêng, 1940) viết về dòng sông Hồng mênh mông và nỗi cô đơn của con người trước vũ trụ. Bài thơ dùng thể thất ngôn với hình ảnh củi khô trôi dạt.", sources: ["Văn 11, Chương 2 — Thơ mới, trang 30–32."]},
      {keys: ["thơ mới"], answer: "Phong trào Thơ mới (1930–1945) đổi mới thơ ca Việt Nam: phá bỏ niêm luật chặt chẽ, đề cao cái tôi cá nhân và cảm xúc. Tiêu biểu: Huy Cận, Xuân Diệu, Hàn Mặc Tử.", sources: ["Văn 11, Chương 2, trang 28."]},
      {keys: [], answer: "Hỏi mình về Thơ mới, “Tràng giang” hoặc “Đây thôn Vĩ Dạ” trong tài liệu Văn 11 nhé.", sources: ["Văn 11, Chương 2 — Thơ mới."]},
    ],
  },
};
function demoContent(sid) { return DEMO_CONTENT[sid] || null; }
function demoChatAnswer(sid, q) {
  const c = demoContent(sid);
  if (!c) return {answer: "Môn này chưa có tài liệu mẫu trong bản demo. Tải tài liệu của môn lên rồi hỏi lại nhé.", sources: []};
  const low = q.toLowerCase();
  const hit = c.chat.find((e) => e.keys.length && e.keys.some((k) => low.includes(k)));
  return hit || c.chat[c.chat.length - 1];
}
const DEMO_LESSONS = DEMO_CONTENT[1].lessons;
const DEMO_QUIZ = DEMO_CONTENT[1].quiz;
const DEMO_DOCS = [
  {id: 1, title: "Sinh học 12 — Chương 2: Quang hợp", subject: "Sinh 12", status: "done", chunks: 48, size: "2,4 MB"},
  {id: 2, title: "Sinh học 12 — Chương 1: Cơ chế di truyền", subject: "Sinh 12", status: "done", chunks: 52, size: "3,1 MB"},
  {id: 3, title: "Văn 11 — Thơ mới (tập ghi chép)", subject: "Văn 11", status: "indexing", chunks: 12, size: "0,8 MB"},
  {id: 4, title: "Toán 12 — Chuyên đề tích phân.pdf", subject: "Toán 12", status: "error", chunks: 0, size: "4,2 MB"},
];
const DEMO_DUE = [
  {qid: 103, q: "Sản phẩm chính của pha tối là gì?", tag: "Sinh 12 · Chương 2"},
  {qid: 203, q: "Tích phân từ 0 đến 1 của 2x dx bằng bao nhiêu?", tag: "Toán 12 · Chương 2"},
  {qid: 301, q: "Tác giả bài thơ “Tràng giang” là ai?", tag: "Văn 11 · Thơ mới"},
];
let assignments = [{cls: "12A1 — Sinh học", title: "Bài tập Chương 2: Quang hợp", due: "20/11"}];
const DEMO_LEAGUE = [
  {name: "Minh Anh", xp: 420, me: true}, {name: "Quốc Bảo", xp: 395},
  {name: "Thu Hằng", xp: 360}, {name: "Đức Anh", xp: 310}, {name: "Phương Linh", xp: 285},
];
const DEMO_CLASSES = [
  {name: "12A1 — Sinh học", students: 38, code: "SINH12A1", xpWeek: 2840},
  {name: "12A2 — Sinh học", students: 35, code: "SINH12A2", xpWeek: 2310},
  {name: "11B — Văn học", students: 41, code: "VAN11B", xpWeek: 1980},
];
const DEMO_STUDENTS = [
  {name: "Quốc Bảo", xp: 395, streak: 12, weak: "Chương 3: Sinh thái"},
  {name: "Thu Hằng", xp: 360, streak: 9, weak: "Chương 2: Quang hợp"},
  {name: "Đức Anh", xp: 310, streak: 4, weak: "Chương 1: Di truyền"},
];
let subjects = DEMO_SUBJECTS.slice();
let docs = DEMO_DOCS.slice();
let progress = {xp: 1240, xpToday: 10, gems: 86, hearts: 5, streak: 7, daily_goal: 30};
function gainXp(n) { progress.xp += n; progress.xpToday = (progress.xpToday || 0) + n; saveProgress(); renderProgress(); }
function saveProgress() { if (demoMode) { try { localStorage.setItem("tuhoc_progress", JSON.stringify(progress)); } catch (e) {} } }
function loadProgress() {
  if (!demoMode) return;
  try { const p = JSON.parse(localStorage.getItem("tuhoc_progress") || "null"); if (p && typeof p.xp === "number") progress = {...progress, ...p}; } catch (e) {}
}

/* ---------- Routing ---------- */
const TITLES = {dashboard: "Trang chủ", subjects: "Môn học", path: "Lộ trình", quiz: "Làm quiz", chat: "Hỏi đáp trên tài liệu", docs: "Tài liệu", essay: "Chấm tự luận", teacher: "Lớp của tôi", profile: "Hồ sơ"};
function showView(id) {
  $$(".view").forEach((v) => v.classList.remove("active"));
  const el = document.getElementById(id);
  if (el) el.classList.add("active");
  window.scrollTo({top: 0});
}
function go(view, arg) {
  if (!$("#app").classList.contains("active")) enterApp();
  if (view === "path" && arg) { const sel = $("#pathSubject"); if (sel) sel.value = String(arg); }
  if (view === "quiz" && arg && arg.subjectId) { const sel = $("#quizSubject"); if (sel) sel.value = String(arg.subjectId); }
  $$("#app .view").forEach((v) => v.classList.remove("active"));
  const el = document.getElementById("view-" + view);
  if (el) el.classList.add("active");
  $$(".nav-item, .bottom-nav button").forEach((b) => b.classList.toggle("active", b.dataset.nav === view));
  $("#topTitle").textContent = TITLES[view] || "TuHoc";
  $("#sidebar").classList.remove("open");
  if (view === "subjects") renderSubjects();
  if (view === "path") renderPath();
  if (view === "quiz") loadQuizQuestions();
  if (view === "docs") renderDocs();
  if (view === "teacher") renderTeacher();
  window.scrollTo({top: 0});
}
function enterApp() {
  showView("app");
  $("#app").classList.add("active");
  $("#sideUser").textContent = demoMode ? "Bạn đang dùng thử (demo)" : (userName + " · " + (role === "teacher" ? "Giáo viên" : "Học sinh"));
  renderAll();
}
function logout() {
  token = ""; role = "student";
  localStorage.removeItem("tuhoc_token"); localStorage.removeItem("tuhoc_role");
  demoMode = true; progress = {xp: 1240, xpToday: 10, gems: 86, hearts: 5, streak: 7, daily_goal: 30};
  showView("landing");
}
$$("[data-goto]").forEach((b) => b.addEventListener("click", () => showView(b.dataset.goto)));
$("#demoBtn").addEventListener("click", () => { demoMode = true; enterApp(); go("dashboard"); });
$("#demoBtn2").addEventListener("click", () => { demoMode = true; enterApp(); go("dashboard"); });

/* ---------- Auth ---------- */
let authMode = "login";
function pickRole(r) {
  role = r;
  $("#roleStudent").setAttribute("aria-pressed", String(r === "student"));
  $("#roleTeacher").setAttribute("aria-pressed", String(r === "teacher"));
}
$("#authSwitch").addEventListener("click", () => {
  authMode = authMode === "login" ? "register" : "login";
  $("#authTitle").textContent = authMode === "login" ? "Đăng nhập để học tiếp" : "Tạo tài khoản TuHoc";
  $("#authSubmit").textContent = authMode === "login" ? "Đăng nhập" : "Tạo tài khoản";
  $("#nameField").hidden = authMode === "login";
  $("#authSwitchText").textContent = authMode === "login" ? "Chưa có tài khoản?" : "Đã có tài khoản?";
  $("#authSwitch").textContent = authMode === "login" ? "Đăng ký ngay" : "Đăng nhập";
  $("#authPassword").setAttribute("autocomplete", authMode === "login" ? "current-password" : "new-password");
});
$("#authForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const email = $("#authEmail").value.trim();
  const password = $("#authPassword").value;
  const name = $("#authName").value.trim() || email.split("@")[0];
  const err = $("#authError");
  err.hidden = true;
  if (password.length < 6) { err.textContent = "Mật khẩu cần tối thiểu 6 ký tự."; err.hidden = false; return; }
  try {
    const path = authMode === "login" ? "/auth/login" : "/auth/register";
    const body = authMode === "login" ? {email, password} : {name, email, password, role};
    const data = await api(path, {method: "POST", body: JSON.stringify(body)});
    token = data.token; userName = name;
    localStorage.setItem("tuhoc_token", token);
    localStorage.setItem("tuhoc_name", name); localStorage.setItem("tuhoc_role", role);
    demoMode = false; enterApp(); go("dashboard");
  } catch (e2) {
    err.textContent = apiLive
      ? "Không đăng nhập được: " + e2.message
      : "Backend chưa chạy nên không đăng nhập được. Bạn có thể bấm “Dùng thử không cần đăng nhập” để xem giao diện demo.";
    err.hidden = false;
  }
});

/* ---------- Shared renders ---------- */
function renderProgress() {
  saveProgress();
  $("#chipStreak").textContent = progress.streak;
  $("#chipXp").textContent = progress.xp.toLocaleString("vi-VN");
  $("#chipHearts").textContent = progress.hearts;
  $("#chipGems").textContent = progress.gems;
  const k = $("#kpiXp"); if (k) k.textContent = (progress.xpToday || 0) + " / " + progress.daily_goal;
  const kd = $("#kpiXpDelta");
  if (kd) { const left = Math.max(0, progress.daily_goal - (progress.xpToday || 0)); kd.textContent = left > 0 ? ("Còn " + left + " XP tới mục tiêu") : "Đã đạt mục tiêu ngày"; }
  const gl = $("#dashGoalLine");
  if (gl) { const left = Math.max(0, progress.daily_goal - (progress.xpToday || 0)); gl.textContent = left > 0 ? ("Hôm nay bạn còn " + left + " XP nữa là đạt mục tiêu ngày. Câu ôn tập đang chờ 3 câu.") : "Bạn đã đạt mục tiêu ngày hôm nay. Câu ôn tập đang chờ 3 câu."; }
  const kh = $("#kpiHearts"); if (kh) kh.textContent = progress.hearts + " / 5";
}
function subjectOptions(sel, list) {
  const el = $(sel); if (!el) return;
  el.innerHTML = list.map((s) => `<option value="${s.id}">${esc(s.name)}</option>`).join("");
}
function greetingFor(hour) {
  if (hour < 11) return "Chào buổi sáng";
  if (hour < 13) return "Chào buổi trưa";
  if (hour < 18) return "Chào buổi chiều";
  return "Chào buổi tối";
}
function subjectName(id) { const s = subjects.find((x) => x.id === Number(id)); return s ? s.name : "môn học"; }
const DEMO_SUGGESTS = {
  1: ["Quang hợp là gì?", "Pha sáng và pha tối khác nhau thế nào?", "Cho ví dụ về quang hợp trong đời sống"],
  2: ["Đạo hàm là gì?", "Tích phân dùng để làm gì?", "Số phức là gì?"],
  3: ["Thơ mới là gì?", "“Tràng giang” nói về điều gì?", "Tác giả bài “Tràng giang” là ai?"],
};
function renderChatSuggests(sid) {
  const box = $("#chatSuggests");
  if (!box) return;
  const list = DEMO_SUGGESTS[sid];
  if (!list) { box.innerHTML = ""; return; }
  box.innerHTML = list.map((q) => `<button class="btn btn-outline" onclick="askSuggest('${q.replace(/'/g, "\'")}')">${esc(q)}</button>`).join("");
}
function syncSubjectLabels() {
  const qid = $("#quizSubject").value || subjects[0].id;
  const q = subjects.find((x) => x.id === Number(qid));
  if (q) $("#quizSub").textContent = q.name + " · Trả lời đúng cộng 10 XP, sai trừ 1 tim.";
  const cid = Number($("#chatSubject").value || subjects[0].id);
  $("#chatInput").placeholder = "Hỏi từ tài liệu " + subjectName(cid) + "…";
  renderChatSuggests(cid);
}
function renderAll() {
  renderProgress();
  renderSubjects(); renderPath(); renderDocs(); renderTeacher(); renderDue();
  subjectOptions("#quizSubject", subjects); subjectOptions("#chatSubject", subjects);
  subjectOptions("#docSubject", subjects); subjectOptions("#essaySubject", subjects);
  subjectOptions("#pathSubject", subjects);
  syncSubjectLabels();
  const hello = $("#dashHello");
  if (hello) hello.textContent = greetingFor(new Date().getHours()) + ", " + userName;
  $("#dashSubjects").innerHTML = subjects.slice(0, 3).map((s) => `
    <div class="list-row"><span class="subj-ic">${esc(s.code || s.name.slice(0, 2))}</span>
      <div class="grow"><p class="title">${esc(s.name)}</p><p class="sub2">${esc(s.desc)}</p></div>
      <span class="pill pill-grey num">${s.progress}%</span></div>`).join("");
  $("#profileName").textContent = userName;
  $("#profileAvatar").textContent = userName.split(" ").map((w) => w[0]).slice(0, 2).join("").toUpperCase();
}
function renderDue() {
  $("#dueList").innerHTML = DEMO_DUE.map((d) => `
    <div class="list-row"><span>●</span><div class="grow"><p class="title" style="font-weight:500">${esc(d.q)}</p><p class="sub2">${esc(d.tag)}</p></div></div>`).join("");
}

/* ---------- Subjects ---------- */
function renderSubjects() {
  const grid = $("#subjectGrid");
  $("#subjectEmpty").hidden = subjects.length > 0;
  grid.innerHTML = subjects.map((s) => `
    <div class="subject-card" role="button" tabindex="0" onclick="openSubject(${s.id})" onkeydown="if(event.key==='Enter')openSubject(${s.id})">
      <span class="subj-ic">${esc(s.code || s.name.slice(0, 2))}</span><h3>${esc(s.name)}</h3><p>${esc(s.desc)}</p>
      <div class="progress-track"><div class="progress-fill" style="width:${s.progress}%"></div></div>
      <div class="row" style="margin-top:8px"><span>${esc(s.lessons)}</span><span class="num">${s.progress}% xong</span></div>
      ${s.custom ? `<button class="btn btn-ghost btn-sm" style="margin-top:8px" onclick="event.stopPropagation();deleteSubject(${s.id})">Xóa môn này</button>` : ""}
    </div>`).join("");
}
function deleteSubject(id) {
  const s = subjects.find((x) => x.id === id);
  if (!s) return;
  if (!confirm("Xóa môn “" + s.name + "”? Môn này và tài liệu của nó sẽ biến mất khỏi danh sách.")) return;
  subjects = subjects.filter((x) => x.id !== id);
  renderSubjects(); renderAll();
}
function loadDemoSubjects() { subjects = DEMO_SUBJECTS.slice(); renderSubjects(); }
async function loadSubjectsFromApi() {
  try { const list = await api("/subjects"); if (Array.isArray(list) && list.length) subjects = list.map((s, i) => ({...s, code: (s.name || "?").slice(0, 2), desc: "", progress: 0, lessons: ""})); } catch (e) { /* giu demo */ }
}
$("#createSubjectForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const name = $("#newSubjectName").value.trim();
  if (!name) return;
  if (!demoMode) {
    try { const s = await api("/subjects", {method: "POST", body: JSON.stringify({name})}); subjects.unshift({id: s.id, name: s.name, code: name.slice(0, 2), desc: "", progress: 0, lessons: "0/20 bài", custom: true}); }
    catch (e2) { alert("Không tạo được môn: " + e2.message); return; }
  } else {
    subjects.unshift({id: Date.now(), name, code: name.slice(0, 2), desc: "Môn tự tạo", progress: 0, lessons: "0/20 bài", custom: true});
  }
  $("#newSubjectName").value = ""; renderSubjects(); renderAll();
});
function openSubject(id) {
  const s = subjects.find((x) => x.id === id);
  if (!s) return;
  $("#pathSubject").value = String(id);
  $("#pathTitle").textContent = "Lộ trình — " + s.name;
  go("path");
}

/* ---------- Learning path ---------- */
let currentChapter = 1; // mac dinh Chuong 2 (Quang hop) khop voi bai hoc mau
function renderPath() {
  const sel = $("#pathSubject");
  const sid = Number(sel.value || subjects[0].id);
  const subj = subjects.find((s) => s.id === sid) || subjects[0];
  $("#pathTitle").textContent = "Lộ trình — " + subj.name;
  const content = demoMode ? demoContent(sid) : null;
  const chapters = content ? content.chapters : ["Chương 1: Kiến thức nền tảng", "Chương 2: Kiến thức trọng tâm", "Chương 3: Ôn tập tổng hợp"];
  if (currentChapter >= chapters.length) currentChapter = 0;
  $("#chapterBar").innerHTML = chapters.map((c, i) =>
    `<button class="btn btn-sm ${i === currentChapter ? "btn-primary" : "btn-outline"}" onclick="pickChapter(${i})">${esc(c)}</button>`).join("");
  if (demoMode && !content) {
    $("#pathSub").textContent = "Môn này chưa có bài học mẫu.";
    $("#pathWrap").innerHTML = `<div class="empty"><h3>Chưa có lộ trình cho ${esc(subj.name)}</h3><p>Tải tài liệu của môn lên, TuHoc sẽ tạo lộ trình theo từng chương.</p><button class="btn btn-accent" onclick="go('docs')">Tải tài liệu lên</button></div>`;
    return;
  }
  const lessons = content ? content.lessons : DEMO_LESSONS;
  $("#pathSub").textContent = chapters[currentChapter] + " · 5 bài · mỗi bài 5 câu, khoảng 5 phút.";
  $("#pathWrap").innerHTML = lessons.map((l, i) => `
    <div class="path-node ${i % 2 === 1 ? "flip" : ""}">
      <span class="node-circle ${l.state}" aria-label="Bài ${l.n}: ${l.state === "done" ? "đã xong" : l.state === "current" ? "đang học" : "đang khóa"}">${l.state === "done" ? '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="m4 12.5 5 5L20 6.5"/></svg>' : l.state === "locked" ? '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="4" y="10" width="16" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/></svg>' : l.n}</span>
      <div class="node-info"><b>${esc(l.title)}</b><span>${esc(l.note)}</span></div>
      ${l.state !== "locked" ? `<button class="btn btn-sm ${l.state === "current" ? "btn-accent" : "btn-outline"}" onclick="startQuiz('${esc(l.title)}')">Học</button>` : ""}
    </div>`).join("");
}
function pickChapter(i) { currentChapter = i; renderPath(); }
let currentLessonTitle = "";
function startQuiz(lessonTitle) {
  currentLessonTitle = lessonTitle || "";
  const sid = Number($("#pathSubject").value || subjects[0].id);
  go("quiz", {subjectId: sid});
}

/* ---------- Quiz ---------- */
let quizQs = [], quizIdx = 0, quizCorrect = 0, quizAnswered = false;
let reviewMode = false;
function currentSubjectId() { return Number($("#quizSubject").value || subjects[0].id); }
function loadQuizQuestions() {
  $("#quizDone").hidden = true;
  reviewMode = false;
  const sid = currentSubjectId();
  const subj = subjects.find((x) => x.id === sid);
  $("#quizSub").textContent = (subj ? subj.name : "Môn học") + (currentLessonTitle ? " — " + currentLessonTitle : "") + " · Trả lời đúng cộng 10 XP, sai trừ 1 tim.";
  currentLessonTitle = "";
  if (progress.hearts <= 0) { quizQs = []; startQuizRun(); return; } // H8: het tim thi chan
  if (!demoMode) {
    api(`/subjects/${sid}/quiz/generate`, {method: "POST", body: JSON.stringify({n: 5})})
      .then((d) => { quizQs = d.questions.map((q) => ({...q, qtype: "mcq", answer_idx: null, _api: true})); startQuizRun(); })
      .catch(() => { quizQs = demoQuestions(sid); startQuizRun(); });
  } else { quizQs = demoQuestions(sid); startQuizRun(); }
}
function demoQuestions(sid) {
  const c = demoContent(sid);
  return c ? c.quiz.slice() : [];
}
/* On tap (M2 + H8): dung dung 3 cau den han; tra loi dung hoi 1 tim thay vi chi cong XP. */
function startReview() {
  reviewMode = true;
  quizQs = DEMO_DUE.map((d) => {
    for (const k of Object.keys(DEMO_CONTENT)) {
      const q = DEMO_CONTENT[k].quiz.find((x) => x.id === d.qid);
      if (q) return q;
    }
    return null;
  }).filter(Boolean);
  $("#quizDone").hidden = true;
  $("#quizSub").textContent = "Ôn tập — 3 câu đến hạn · Trả lời đúng hồi 1 tim.";
  if (progress.hearts >= 5) { alert("Tim của bạn đang đầy (5/5). Không cần ôn để hồi tim lúc này."); reviewMode = false; return; }
  startQuizRun();
}
function startQuizRun() {
  quizIdx = 0; quizCorrect = 0; quizAnswered = false;
  $("#quizEmpty").hidden = quizQs.length > 0;
  if (progress.hearts <= 0 && !reviewMode) {
    $("#quizBox").innerHTML = `<div class="empty"><h3>Hết tim rồi</h3><p>Bạn đã sai quá nhiều trong ngày hôm nay. Ôn lại câu đến hạn để hồi tim (mỗi câu đúng hồi 1 tim), hoặc dùng 10 gem để hồi 1 tim ngay.</p>
      <button class="btn btn-accent" onclick="startReview()">Ôn 3 câu đến hạn</button>
      <button class="btn btn-outline" onclick="spendGemsForHeart()" ${progress.gems < 10 ? "disabled" : ""}>Dùng 10 gem hồi 1 tim (đang có ${progress.gems})</button></div>`;
    return;
  }
  $("#quizBox").innerHTML = "";
  renderQuizQ();
}
function spendGemsForHeart() {
  if (progress.gems < 10 || progress.hearts >= 5) return;
  progress.gems -= 10; progress.hearts += 1;
  saveProgress(); renderProgress(); loadQuizQuestions();
}
function renderQuizQ() {
  const q = quizQs[quizIdx];
  if (!q) { showQuizDone(); return; }
  quizAnswered = false;
  $("#quizCounter").textContent = "Câu " + (quizIdx + 1) + "/" + quizQs.length;
  $("#quizBar").style.width = (((quizIdx + 1) / quizQs.length) * 100) + "%"; // N9: dang o cau 1/5 thi 20%, khong phai 0%
  $("#quizHearts").textContent = progress.hearts;
  let body = "";
  if (q.qtype === "fill") {
    body = `<p style="font-size:18px;font-weight:600;margin-bottom:16px">${esc(q.question)}</p>
      <div class="fill-answer"><input class="input" id="fillInput" placeholder="Điền từ còn thiếu…" aria-label="Đáp án điền khuyết"><button class="btn btn-accent" onclick="answerFill()">Trả lời</button></div>
      <div id="quizFb"></div>`;
  } else {
    body = `<p style="font-size:18px;font-weight:600;margin-bottom:16px">${esc(q.question)}</p>
      ${q.options.map((o, i) => `<button class="option" onclick="answerOption(${i}, this)"><span class="key">${"ABCD"[i]}</span><span>${esc(o)}</span></button>`).join("")}
      <div id="quizFb"></div>`;
  }
  $("#quizBox").innerHTML = body;
}
function showFeedback(ok, text) {
  const q = quizQs[quizIdx];
  const qh = $("#quizHearts"); if (qh) qh.textContent = progress.hearts;
  $("#quizFb").innerHTML = `<div class="feedback ${ok ? "correct" : "wrong"}" role="status">
    <h3>${ok ? (reviewMode ? "Chính xác. Cộng 5 XP, hồi 1 tim." : "Chính xác. Cộng 10 XP.") : "Chưa đúng. Trừ 1 tim."}</h3>
    <p>${esc(text)}</p>
    <p class="src"><b>Nguồn:</b> ${esc(q.source || "Tài liệu trong môn học.")}</p>
    <div style="height:12px"></div>
    <button class="btn btn-primary" onclick="nextQuizQ()">${quizIdx + 1 >= quizQs.length ? "Xem kết quả" : "Câu tiếp theo"}</button>
  </div>`;
  $("#quizBar").style.width = ((quizIdx + 1) / quizQs.length * 100) + "%";
}
async function answerOption(i, btn) {
  if (quizAnswered) return;
  quizAnswered = true;
  const q = quizQs[quizIdx];
  $$(".option").forEach((b) => b.disabled = true);
  if (q._api && !demoMode) {
    try {
      const r = await api(`/quiz/${q.id}/answer`, {method: "POST", body: JSON.stringify({answer_idx: i})});
      progress = {...progress, ...r.progress}; // H7: server giu tong XP/tim; xpToday chi la bo dem phien o client, cong dung 1 lan
      btn.classList.add(r.correct ? "correct" : "wrong");
      if (r.correct) { quizCorrect++; progress.xpToday = (progress.xpToday || 0) + 10; }
      renderProgress(); showFeedback(r.correct, r.explanation || "");
      return;
    } catch (e) { /* roi ve cham local */ }
  }
  const ok = i === q.answer_idx;
  btn.classList.add(ok ? "correct" : "wrong");
  if (!ok) { const right = $$(".option")[q.answer_idx]; if (right) right.classList.add("correct"); }
  if (ok) {
    quizCorrect++;
    if (reviewMode) { progress.hearts = Math.min(5, progress.hearts + 1); gainXp(5); markDueDone(q.id); }
    else gainXp(10);
  } else { progress.hearts = Math.max(0, progress.hearts - 1); }
  renderProgress(); showFeedback(ok, q.explanation);
}
function normFill(v) {
  return (v || "").trim().toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/[^a-z0-9]/g, "");
}
function answerFill() {
  if (quizAnswered) return;
  const q = quizQs[quizIdx];
  const v = normFill($("#fillInput").value);
  quizAnswered = true;
  const accepted = [q.answer_text].concat(q.answer_alt || []).map(normFill);
  const ok = accepted.includes(v) && v.length > 0;
  if (ok) {
    quizCorrect++;
    if (reviewMode) { progress.hearts = Math.min(5, progress.hearts + 1); gainXp(5); markDueDone(q.id); }
    else gainXp(10);
  } else { progress.hearts = Math.max(0, progress.hearts - 1); }
  renderProgress();
  showFeedback(ok, ok ? q.explanation : ("Đáp án đúng là “" + q.answer_text + "”. " + q.explanation));
}
function markDueDone(qid) {
  const i = DEMO_DUE.findIndex((d) => d.qid === qid);
  if (i >= 0) { DEMO_DUE.splice(i, 1); renderDue(); }
}
function nextQuizQ() { quizIdx++; renderQuizQ(); }
function showQuizDone() {
  const box = $("#quizDone");
  box.hidden = false;
  let extra = "";
  if (!reviewMode && quizQs.length >= 5 && quizCorrect === quizQs.length) {
    progress.gems += 5; saveProgress(); renderProgress();
    extra = `<p class="sub" style="margin-top:4px">Đúng cả ${quizQs.length} câu — thưởng thêm 5 gem.</p>`;
  }
  if (reviewMode) {
    extra = `<p class="sub" style="margin-top:4px">Đã ôn xong. Mỗi câu đúng đã hồi 1 tim — tim hiện tại ${progress.hearts}/5.</p>`;
    reviewMode = false;
  }
  box.innerHTML = `<div class="card" style="text-align:center">
    <h3>Xong bài quiz</h3>
    <p class="sub" style="margin-top:4px">Bạn đúng ${quizCorrect}/${quizQs.length} câu · Tim còn ${progress.hearts}/5 · Gem: ${progress.gems}</p>
    ${extra}
    <div style="height:12px"></div>
    <button class="btn btn-accent" onclick="loadQuizQuestions()">Làm bài mới</button>
    <button class="btn btn-outline" onclick="go('path')">Về lộ trình</button></div>`;
  $("#quizBox").innerHTML = "";
}

/* ---------- Chat RAG ---------- */
function chatMsg(role2, text, sources) {
  const log = $("#chatLog");
  const div = document.createElement("div");
  div.className = "msg " + role2;
  div.innerHTML = esc(text) + (sources && sources.length ? `<details class="srcs"><summary>Nguồn trích dẫn (${sources.length})</summary>${sources.map((s) => `<p style="margin-top:6px">• ${esc(typeof s === "string" ? s : (s.text || ""))}</p>`).join("")}</details>` : "");
  log.appendChild(div);
  log.scrollTop = log.scrollHeight;
}
function askSuggest(q) { $("#chatInput").value = q; $("#chatForm").requestSubmit(); }
function setChatBusy(busy) {
  $("#chatInput").disabled = busy;
  $("#chatForm button[type=submit]").disabled = busy;
  let t = $("#typingMsg");
  if (busy && !t) {
    const log = $("#chatLog");
    t = document.createElement("div");
    t.className = "msg bot"; t.id = "typingMsg"; t.textContent = "Đang tìm trong tài liệu…";
    log.appendChild(t); log.scrollTop = log.scrollHeight;
  } else if (!busy && t) { t.remove(); }
}
$("#chatForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const q = $("#chatInput").value.trim();
  if (!q) return;
  $("#chatInput").value = "";
  chatMsg("user", q);
  const sid = Number($("#chatSubject").value || subjects[0].id);
  setChatBusy(true);
  if (demoMode) {
    setTimeout(() => {
      const a = demoChatAnswer(sid, q);
      setChatBusy(false);
      chatMsg("bot", a.answer, a.sources);
      gainXp(5);
    }, 500);
    return;
  }
  try {
    const r = await api(`/subjects/${sid}/chat`, {method: "POST", body: JSON.stringify({question: q})});
    setChatBusy(false);
    chatMsg("bot", r.answer, r.sources);
    // H7: server giu tong XP; client chi cong bo dem xpToday cua phien, dung 1 lan.
    progress.xpToday = (progress.xpToday || 0) + 5;
    try { const me = await api("/me"); progress = {...progress, xpToday: progress.xpToday, ...me}; } catch (e3) {}
    renderProgress();
  } catch (e2) {
    setChatBusy(false);
    chatMsg("bot", "Không hỏi được lúc này: " + e2.message + " Hãy kiểm tra backend rồi thử lại.");
  }
});
function renderChatDocs() {
  const sid = Number($("#chatSubject").value || subjects[0].id);
  const subjName = subjectName(sid);
  $("#chatDocs").innerHTML = docs.filter((d) => d.subject === subjName && d.status === "done").map((d) =>
    `<p style="font-size:14px;margin-bottom:8px">• ${esc(d.title)} <span class="meta">(${d.chunks} đoạn)</span></p>`).join("")
    || `<p class="meta">Chưa có tài liệu trong môn này.</p>`;
}
async function uploadFromChat() {
  const f = $("#chatFile").files[0];
  const msg = $("#chatUploadMsg");
  if (!f) { msg.textContent = "Hãy chọn một file PDF, DOCX, TXT hoặc MD trước."; return; }
  if (demoMode) {
    docs.unshift({id: Date.now(), title: f.name, subject: subjectName(sid), status: "indexing", chunks: 0, size: (f.size / 1048576).toFixed(1) + " MB"});
    renderDocs();
    msg.textContent = "Demo: đã nhận “" + f.name + "”. Khi backend chạy, file sẽ được lập chỉ mục thật.";
    return;
  }
  const sid = Number($("#chatSubject").value || subjects[0].id);
  const fd = new FormData(); fd.append("file", f);
  try {
    const r = await apiForm(`/subjects/${sid}/docs`, fd);
    docs.unshift({id: Date.now(), title: f.name, subject: subjectName(sid), status: "indexing", chunks: 0, size: (f.size / 1048576).toFixed(1) + " MB"});
    renderDocs();
    msg.textContent = "Đã tải lên. Trạng thái: " + (r.status || "đang lập chỉ mục") + ".";
  }
  catch (e2) { msg.textContent = "Tải lên thất bại: " + e2.message; }
}

/* ---------- Docs ---------- */
function statusPill(s) {
  if (s === "done") return `<span class="pill pill-green"><span class="dot"></span>Đã xong</span>`;
  if (s === "indexing") return `<span class="pill pill-amber"><span class="dot"></span>Đang lập chỉ mục</span>`;
  return `<span class="pill pill-red"><span class="dot"></span>Lỗi đọc file</span>`;
}
function renderDocs() {
  const tb = $("#docTable");
  $("#docEmpty").hidden = docs.length > 0;
  tb.innerHTML = docs.map((d) => `<tr>
    <td><b>${esc(d.title)}</b><br><span class="meta">${esc(d.size || "")}</span></td>
    <td>${esc(d.subject)}</td><td>${statusPill(d.status)}</td>
    <td class="num">${d.status === "done" ? d.chunks : "—"}</td>
    <td style="text-align:right">${d.status === "error" ? `<button class="btn btn-outline btn-sm" onclick="retryDoc(${d.id})">Thử lại</button> ` : ""}<button class="btn btn-ghost btn-sm" onclick="deleteDoc(${d.id})">Xóa tài liệu</button></td>
  </tr>`).join("");
  renderChatDocs();
}
async function retryDoc(id) {
  const d = docs.find((x) => x.id === id);
  if (!d) return;
  if (!demoMode) {
    try {
      const r = await api(`/docs/${id}/retry`, {method: "POST"});
      d.status = r.status || "done"; d.chunks = (r.chunks ?? d.chunks); renderDocs();
    } catch (e2) { alert("Thử lại thất bại: " + e2.message); }
    return;
  }
  d.status = "indexing"; renderDocs();
  setTimeout(() => { d.status = "done"; d.chunks = 36; renderDocs(); }, 1200);
}
async function deleteDoc(id) {
  const d = docs.find((x) => x.id === id);
  if (!d) return;
  if (!demoMode) {
    if (!confirm("Xóa tài liệu “" + d.title + "”? Các đoạn đã lập chỉ mục của nó cũng bị xóa.")) return;
    try { await api(`/docs/${id}`, {method: "DELETE"}); docs = docs.filter((x) => x.id !== id); renderDocs(); }
    catch (e2) { alert("Xóa thất bại: " + e2.message); }
    return;
  }
  if (!confirm("Xóa tài liệu “" + d.title + "”? Các đoạn đã lập chỉ mục của nó cũng bị xóa. (Demo — chỉ xóa trên máy này.)")) return;
  docs = docs.filter((x) => x.id !== id); renderDocs();
}
$("#docForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const title = $("#docTitle").value.trim();
  const file = $("#docFile").files[0];
  const text = $("#docText").value.trim();
  const msg = $("#docMsg");
  if (!title || (!file && text.length < 20)) { msg.textContent = "Cần tiêu đề và file hoặc nội dung từ 20 ký tự trở lên."; return; }
  if (demoMode) {
    docs.unshift({id: Date.now(), title, subject: $("#docSubject").selectedOptions[0].textContent, status: "indexing", chunks: 0, size: file ? (file.size / 1048576).toFixed(1) + " MB" : "văn bản dán"});
    msg.textContent = "Demo: đã nhận file, đang lập chỉ mục (mẫu).";
    renderDocs(); return;
  }
  try {
    const sidVal = $("#docSubject").value;
    if (file) { const fd = new FormData(); fd.append("file", file); await apiForm(`/subjects/${sidVal}/docs`, fd); }
    else { await api(`/subjects/${sidVal}/docs`, {method: "POST", body: JSON.stringify({title, text})}); }
    docs.unshift({id: Date.now(), title, subject: subjectName(sidVal), status: "indexing", chunks: 0, size: file ? (file.size / 1048576).toFixed(1) + " MB" : "văn bản dán"});
    renderDocs();
    msg.textContent = "Đã tải lên, đang lập chỉ mục.";
  } catch (e2) { msg.textContent = "Tải lên thất bại: " + e2.message; }
});

/* ---------- Essay ---------- */
function fillEssaySample() {
  $("#essayPrompt").value = "Trình bày vai trò của quang hợp đối với sự sống trên Trái Đất.";
  $("#essayRubric").value = "Nêu đúng khái niệm quang hợp - 2đ\nPhân tích vai trò với cây xanh và môi trường - 3đ\nLiên hệ thực tế, lấy ví dụ - 2đ\nTrình bày rõ ràng, đúng chính tả - 1đ";
  $("#essayText").value = "Quang hợp là quá trình cây xanh dùng năng lượng ánh sáng để tổng hợp chất hữu cơ từ nước và khí cacbonic. Nhờ quang hợp, cây tạo ra oxi cho con người hít thở và tạo ra thức ăn cho các sinh vật khác. Nếu không có quang hợp, sự sống trên Trái Đất sẽ không duy trì được.";
}
function renderEssayResult(r) {
  const body = $("#essayResultBody");
  body.innerHTML = `
    <div class="essay-total"><b class="num">${r.total}</b><span>/ ${r.max_total} điểm · ${r.mode === "llm" ? "Chấm bằng AI theo barem" : "Chấm tạm — cần backend để chấm thật"}</span></div>
    <p style="margin-top:8px;color:var(--ink-2);font-size:15px">${esc(r.overall || "")}</p>
    <div style="height:16px"></div>
    <table><thead><tr><th>Tiêu chí</th><th class="num">Điểm</th><th>Nhận xét và gợi ý sửa</th></tr></thead><tbody>
    ${r.scores.map((s) => `<tr><td><b>${esc(s.criterion)}</b>${s.quote ? `<br><span class="meta">Trích bài làm: “${esc(s.quote)}”</span>` : ""}</td>
      <td class="num"><b>${s.score}</b> / ${s.max}</td><td>${esc(s.feedback)}<div class="score-bar" style="margin-top:6px"><span style="width:${Math.round(s.score / s.max * 100)}%"></span></div></td></tr>`).join("")}
    </tbody></table>
    <p class="meta" style="margin-top:12px">Điểm này do AI chấm theo barem. Giáo viên duyệt và sửa điểm trước khi gửi cho học sinh.</p>
    <div style="height:12px"></div>
    <button class="btn btn-outline" onclick="sendToTeacher(this)">Gửi cho giáo viên duyệt</button><span class="meta" id="essaySent"></span>`;
}
$("#essayForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const btn = $("#essaySubmit");
  btn.disabled = true; btn.textContent = "Đang chấm…";
  $("#essayError").hidden = true;
  const payload = {prompt: $("#essayPrompt").value.trim(), rubric: $("#essayRubric").value.trim(), essay: $("#essayText").value.trim()};
  if (payload.essay.length < 20) {
    const er = $("#essayError"); er.textContent = "Bài làm cần ít nhất 20 ký tự để chấm được."; er.hidden = false;
    btn.disabled = false; btn.textContent = "Chấm bài này"; return;
  }
  if (demoMode) {
    setTimeout(() => {
      renderEssayResult({total: 6.5, max_total: 8, mode: "demo",
        overall: "Bài làm nêu đúng khái niệm và vai trò chính, nhưng phần liên hệ thực tế còn chung chung, chưa có ví dụ cụ thể.",
        scores: [
          {criterion: "Nêu đúng khái niệm quang hợp", score: 2, max: 2, quote: "Quang hợp là quá trình cây xanh dùng năng lượng ánh sáng…", feedback: "Nêu đúng và đủ ý."},
          {criterion: "Phân tích vai trò với cây xanh và môi trường", score: 2.5, max: 3, quote: "Nhờ quang hợp, cây tạo ra oxi cho con người hít thở…", feedback: "Đủ ý chính, có thể nói thêm về cân bằng khí cacbonic."},
          {criterion: "Liên hệ thực tế, lấy ví dụ", score: 1, max: 2, quote: "", feedback: "Chưa có ví dụ cụ thể. Thêm ví dụ: rừng giúp giảm hiệu ứng nhà kính."},
          {criterion: "Trình bày rõ ràng, đúng chính tả", score: 1, max: 1, quote: "", feedback: "Trình bày mạch lạc, không lỗi chính tả."}]});
      gainXp(50);
      btn.disabled = false; btn.textContent = "Chấm bài này";
    }, 600);
    return;
  }
  try {
    const sid = Number($("#essaySubject").value || subjects[0].id);
    const r = await api(`/subjects/${sid}/essay/grade`, {method: "POST", body: JSON.stringify(payload)});
    renderEssayResult(r);
    progress.xpToday = (progress.xpToday || 0) + 50;
    try { const me = await api("/me"); progress = {...progress, xpToday: progress.xpToday, ...me}; } catch (e3) {}
    renderProgress();
  } catch (e2) {
    const er = $("#essayError"); er.textContent = "Chấm thất bại: " + e2.message; er.hidden = false;
  }
  btn.disabled = false; btn.textContent = "Chấm bài này";
});

function sendToTeacher(btn) {
  try {
    const pending = JSON.parse(localStorage.getItem("tuhoc_pending") || "[]");
    pending.unshift({prompt: $("#essayPrompt").value.trim(), total: document.querySelector("#essayResultBody .essay-total b")?.textContent || "?", date: new Date().toLocaleDateString("vi-VN")});
    localStorage.setItem("tuhoc_pending", JSON.stringify(pending.slice(0, 20)));
  } catch (e) {}
  const note = $("#essaySent");
  if (note) note.textContent = "Đã gửi cho giáo viên duyệt (demo — lưu trên máy này).";
  if (btn) btn.disabled = true;
  renderTeacher();
}

/* ---------- Teacher ---------- */
function renderTeacher() {
  $("#leagueList").innerHTML = DEMO_LEAGUE.map((s, i) => `
    <div class="league-row"><span class="rank ${i === 0 ? "first" : ""}">${i + 1}</span>
      <div class="grow"><b>${esc(s.name)}</b>${s.me ? ' <span class="pill pill-green">Bạn</span>' : ""}</div>
      <span class="num"><b>${s.xp}</b> XP</span></div>`).join("");
  $("#classList").innerHTML = DEMO_CLASSES.map((c) => `
    <div class="list-row"><span class="subj-ic">Lớp</span>
      <div class="grow"><p class="title">${esc(c.name)}</p><p class="sub2">${c.students} học sinh · Mã lớp ${c.code} · ${c.xpWeek.toLocaleString("vi-VN")} XP tuần này</p></div>
      <button class="btn btn-outline btn-sm" onclick="assignWork('${esc(c.name)}')">Giao bài</button></div>`).join("");
  $("#assignList").innerHTML = assignments.length
    ? assignments.map((a) => `<div class="list-row"><div class="grow"><p class="title" style="font-weight:500">${esc(a.title)}</p><p class="sub2">${esc(a.cls)} · Hạn: ${esc(a.due)}</p></div></div>`).join("")
    : `<p class="meta">Chưa giao bài nào cho lớp.</p>`;
  let pending = [];
  try { pending = JSON.parse(localStorage.getItem("tuhoc_pending") || "[]"); } catch (e) {}
  $("#pendingList").innerHTML = pending.length
    ? `<p style="font-size:14px"><b>${pending.length} bài tự luận đang chờ duyệt.</b> Bài mới nhất: “${esc(pending[0].prompt.slice(0, 60))}…” — ${esc(pending[0].total)} điểm (chấm tạm), ngày ${esc(pending[0].date)}.</p>`
    : `<p class="meta">Chưa có bài tự luận nào chờ duyệt.</p>`;
  $("#studentTable").innerHTML = DEMO_STUDENTS.map((s) => `
    <div class="list-row"><div class="grow"><p class="title">${esc(s.name)}</p><p class="sub2">Streak ${s.streak} ngày · Yếu: ${esc(s.weak)}</p></div>
      <span class="num"><b>${s.xp}</b> XP</span></div>`).join("");
}
function assignWork(clsName) {
  const title = prompt("Giao bài cho " + clsName + " — nhập tên bài (ví dụ: Bài tập Chương 2: Quang hợp):");
  if (!title) return;
  const due = prompt("Hạn nộp (ví dụ: 20/11):", "20/11") || "—";
  assignments.unshift({cls: clsName, title, due});
  renderTeacher();
}
async function createClass() {
  const name = prompt("Tên lớp mới (ví dụ: 12A3 — Sinh học):");
  if (!name) return;
  if (!demoMode) {
    try {
      const c = await api("/classes", {method: "POST", body: JSON.stringify({name})});
      const list = await api("/classes");
      if (Array.isArray(list)) { DEMO_CLASSES.length = 0; list.forEach((x) => DEMO_CLASSES.push({id: x.id, name: x.name, students: x.students || 0, code: x.code || "", xpWeek: 0})); }
      else DEMO_CLASSES.unshift({name: c.name || name, students: 0, code: c.code || "", xpWeek: 0});
    } catch (e2) { alert("Không tạo được lớp: " + e2.message); return; }
  } else {
    DEMO_CLASSES.unshift({name, students: 0, code: "MOI" + Math.floor(Math.random() * 900 + 100), xpWeek: 0});
  }
  renderTeacher();
}
async function gradeBatch() {
  const m = $("#batchMsg");
  if (!demoMode) {
    // Noi endpoint that: dung lop dau tien trong danh sach (da load tu API).
    const cls = DEMO_CLASSES[0];
    if (!cls || !cls.id) { m.innerHTML = `<p style="font-size:14px">Chưa có lớp nào. Tạo lớp trước rồi chấm hàng loạt.</p>`; return; }
    m.innerHTML = `<p style="font-size:14px">Đang chấm các bài chờ duyệt của lớp ${esc(cls.name)} theo barem…</p>`;
    try {
      const r = await api(`/classes/${cls.id}/essays/grade-batch`, {method: "POST", body: JSON.stringify({prompt: "Chấm bài tự luận của lớp", rubric: "Nội dung - 8đ\nTrình bày - 2đ"})});
      m.innerHTML = `<p style="font-size:14px"><b>Đã chấm xong ${r.graded}/${r.total} bài.</b> Điểm trung bình ${r.average}/10. Giáo viên bấm vào từng bài để sửa điểm rồi gửi cho lớp.</p>`;
    } catch (e2) { m.innerHTML = `<p style="font-size:14px">Chấm hàng loạt thất bại: ${esc(e2.message)}</p>`; }
    return;
  }
  m.innerHTML = `<p style="font-size:14px">Đang chấm 12 bài theo barem… (demo — không lưu lên server.)</p>`;
  setTimeout(() => { m.innerHTML = `<p style="font-size:14px"><b>Đã chấm xong 12/12 bài (demo).</b> Điểm trung bình 6,8/10. Giáo viên bấm vào từng bài để sửa điểm rồi gửi cho lớp.</p>`; }, 900);
}
function exportCSV() {
  const rows = [["Học sinh", "XP tuần", "Streak (ngày)", "Điểm yếu"], ...DEMO_STUDENTS.map((s) => [s.name, s.xp, s.streak, s.weak])];
  const csv = "﻿" + rows.map((r) => r.map((v) => '"' + String(v).replace(/"/g, '""') + '"').join(",")).join("\n");
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([csv], {type: "text/csv;charset=utf-8"}));
  a.download = "bang-diem-tuan.csv"; a.click();
  URL.revokeObjectURL(a.href);
}

/* ---------- Profile ---------- */
$("#profileForm").addEventListener("submit", (e) => {
  e.preventDefault();
  progress.daily_goal = Number($("#dailyGoal").value);
  const remind = $("#remindTime").value;
  try { localStorage.setItem("tuhoc_remind", remind); } catch (e2) {}
  $("#profileMsg").textContent = "Đã lưu mục tiêu " + progress.daily_goal + " XP mỗi ngày, nhắc ôn lúc " + remind + ".";
  saveProgress(); renderProgress();
});

/* ---------- File inputs: hien ten file da chon (N5, khong dung chu tieng Anh cua trinh duyet) ---------- */
function wireFileName(inputId, labelId) {
  const input = $(inputId), label = $(labelId);
  if (!input || !label) return;
  input.addEventListener("change", () => { label.textContent = input.files[0] ? input.files[0].name : "Chưa chọn file nào."; });
}
wireFileName("#chatFile", "#chatFileName");
wireFileName("#docFile", "#docFileName");

/* ---------- Doi mon o cac select phai doi noi dung ngay (khong cho toi khi chuyen man hinh) ---------- */
$("#pathSubject").addEventListener("change", renderPath);
$("#quizSubject").addEventListener("change", loadQuizQuestions);
$("#chatSubject").addEventListener("change", () => { syncSubjectLabels(); renderChatDocs(); });

/* ---------- Init ---------- */
(async function init() {
  await checkHealth();
  loadProgress();
  try { const savedRemind = localStorage.getItem("tuhoc_remind"); if (savedRemind) $("#remindTime").value = savedRemind; } catch (e) {}
  if (!demoMode) { await loadSubjectsFromApi(); try { const me = await api("/me"); progress = {...progress, ...me}; } catch (e) {} }
  if (token) { enterApp(); go("dashboard"); }
  else {
    chatMsg("bot", "Chào bạn, mình là trợ lý học tập của TuHoc. Chọn một môn ở khung bên phải rồi hỏi mình bất cứ gì trong tài liệu của môn đó nhé.", []);
    renderAll();
  }
  renderProgress();
})();
