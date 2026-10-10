import { useEffect, useState } from "react";
import { api } from "../api.js";

const fmt = (iso) => new Date(iso).toLocaleString("vi-VN");

function windowState(exam) {
  const now = Date.now();
  if (now < new Date(exam.start_time)) return "Chưa mở";
  if (now > new Date(exam.end_time)) return "Đã đóng";
  return "Đang mở";
}

export default function ExamList({ user, go }) {
  const [exams, setExams] = useState(null);
  const [attempts, setAttempts] = useState({}); // exam_id -> attempt (chỉ sinh viên)
  const [error, setError] = useState("");

  const isStudent = user.role === "student";

  async function load() {
    try {
      const list = await api("/api/exams");
      setExams(list);
      if (isStudent) {
        const mine = await api("/api/attempts");
        setAttempts(Object.fromEntries(mine.map((a) => [a.exam_id, a])));
      }
    } catch (err) {
      setError(err.message);
    }
  }
  useEffect(() => {
    load();
  }, []);

  async function publish(id) {
    try {
      await api(`/api/exams/${id}/publish`, { method: "POST" });
      load();
    } catch (err) {
      setError(err.message);
    }
  }

  if (error) return <p className="error">{error}</p>;
  if (!exams) return <p>Đang tải...</p>;

  return (
    <div>
      <h1>{isStudent ? "Đề thi dành cho bạn" : "Đề thi của tôi"}</h1>
      {exams.length === 0 && <p>Chưa có đề thi nào.</p>}
      {exams.map((e) => {
        const state = windowState(e);
        const attempt = attempts[e.id];
        return (
          <div className="card" key={e.id}>
            <div className="row">
              <h2>{e.title}</h2>
              <span className={`badge ${state === "Đang mở" ? "ok" : ""}`}>{state}</span>
            </div>
            <p className="muted">
              {e.question_count} câu · {e.duration_minutes} phút · {fmt(e.start_time)} → {fmt(e.end_time)}
              {!isStudent && (e.is_published ? " · Đã công bố" : " · Bản nháp")}
            </p>
            {isStudent ? (
              attempt?.submitted ? (
                <button onClick={() => go("result", { attemptId: attempt.id })}>Xem kết quả</button>
              ) : (
                <button disabled={state !== "Đang mở" && !attempt} onClick={() => go("take", { examId: e.id })}>
                  {attempt ? "Tiếp tục làm bài" : "Làm bài"}
                </button>
              )
            ) : (
              <div className="row-gap">
                {!e.is_published && <button onClick={() => publish(e.id)}>Công bố</button>}
                <button onClick={() => go("results", { examId: e.id })}>Bảng điểm</button>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
