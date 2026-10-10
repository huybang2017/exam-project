import { useCallback, useEffect, useRef, useState } from "react";
import { api, session, WS_BASE } from "../api.js";

const mmss = (s) => `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;
const SAVE_DELAY_MS = 500; // debounce autosave

export default function TakeExam({ examId, go }) {
  const [attempt, setAttempt] = useState(null);
  const [answers, setAnswers] = useState({}); // question_id -> choice_id
  const [remaining, setRemaining] = useState(null);
  const [saveState, setSaveState] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const pending = useRef({}); // đáp án chưa gửi lên server
  const timer = useRef(null);
  const finished = useRef(false);

  const finish = useCallback(
    (attemptId) => {
      if (finished.current) return;
      finished.current = true;
      go("result", { attemptId });
    },
    [go]
  );

  // 1) Bắt đầu / vào lại bài làm (idempotent nên F5 an toàn)
  useEffect(() => {
    api(`/api/exams/${examId}/attempts`, { method: "POST" })
      .then((a) => {
        if (a.submitted) return finish(a.id);
        setAttempt(a);
        setRemaining(a.remaining_seconds);
        setAnswers(Object.fromEntries(Object.entries(a.saved_answers).map(([q, c]) => [Number(q), c])));
      })
      .catch((err) => setError(err.message));
  }, [examId, finish]);

  // 2) Đồng hồ do server đẩy qua WebSocket
  useEffect(() => {
    if (!attempt) return;
    const ws = new WebSocket(`${WS_BASE}/ws/attempts/${attempt.id}?token=${encodeURIComponent(session.token)}`);
    ws.onmessage = (ev) => {
      const msg = JSON.parse(ev.data);
      if (msg.remaining !== undefined) setRemaining(msg.remaining);
      else if (msg.event) finish(attempt.id); // expired | submitted
    };
    return () => ws.close();
  }, [attempt, finish]);

  // 3) Tự động lưu đáp án (debounce 500 ms)
  const flush = useCallback(async () => {
    if (!attempt || Object.keys(pending.current).length === 0) return;
    const batch = Object.entries(pending.current).map(([q, c]) => ({ question_id: Number(q), choice_id: c }));
    pending.current = {};
    setSaveState("Đang lưu...");
    try {
      await api(`/api/attempts/${attempt.id}/answers`, { method: "PUT", json: { answers: batch } });
      setSaveState("Đã lưu");
    } catch (err) {
      batch.forEach((a) => (pending.current[a.question_id] ??= a.choice_id)); // thử lại lần sau
      setSaveState(`Lưu thất bại: ${err.message}`);
    }
  }, [attempt]);

  function choose(questionId, choiceId) {
    setAnswers((prev) => ({ ...prev, [questionId]: choiceId }));
    pending.current[questionId] = choiceId;
    clearTimeout(timer.current);
    timer.current = setTimeout(flush, SAVE_DELAY_MS);
  }

  async function submit() {
    if (!window.confirm("Nộp bài? Bạn không thể sửa sau khi nộp.")) return;
    setSubmitting(true);
    clearTimeout(timer.current);
    await flush();
    try {
      await api(`/api/attempts/${attempt.id}/submit`, { method: "POST" });
      finish(attempt.id);
    } catch (err) {
      setError(err.message);
      setSubmitting(false);
    }
  }

  if (error) return <p className="error">{error}</p>;
  if (!attempt) return <p>Đang tải đề...</p>;

  const answered = Object.keys(answers).length;
  return (
    <div>
      <div className="exam-bar">
        <span>
          Đã làm {answered}/{attempt.questions.length}
        </span>
        <span className={`clock ${remaining !== null && remaining < 60 ? "danger" : ""}`}>
          {remaining === null ? "--:--" : mmss(remaining)}
        </span>
        <span className="muted">{saveState}</span>
      </div>

      {attempt.questions.map((q, i) => (
        <div className="card" key={q.id}>
          <p>
            <strong>Câu {i + 1}.</strong> {q.content}
          </p>
          {q.choices.map((c) => (
            <label className="choice" key={c.id}>
              <input type="radio" name={`q${q.id}`} checked={answers[q.id] === c.id} onChange={() => choose(q.id, c.id)} />
              {c.text}
            </label>
          ))}
        </div>
      ))}

      <button onClick={submit} disabled={submitting}>
        {submitting ? "Đang nộp..." : "Nộp bài"}
      </button>
    </div>
  );
}
