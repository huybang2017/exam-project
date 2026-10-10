import { useEffect, useState } from "react";
import { api } from "../api.js";

export default function Results({ examId, go }) {
  const [rows, setRows] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api(`/api/exams/${examId}/results`).then(setRows).catch((err) => setError(err.message));
  }, [examId]);

  // Tải CSV bằng fetch để gắn được header Authorization (thẻ <a> thường không làm được)
  async function downloadCsv() {
    try {
      const blob = await api(`/api/exams/${examId}/results.csv`, { blob: true });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `exam_${examId}_results.csv`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err.message);
    }
  }

  if (error) return <p className="error">{error}</p>;
  if (!rows) return <p>Đang tải...</p>;

  const scored = rows.filter((r) => r.score !== null);
  const avg = scored.length ? (scored.reduce((s, r) => s + r.score, 0) / scored.length).toFixed(2) : "–";

  return (
    <div>
      <div className="row">
        <h1>Bảng điểm đề #{examId}</h1>
        <div className="row-gap">
          <button onClick={downloadCsv}>Tải CSV</button>
          <button className="secondary" onClick={() => go("exams")}>
            Quay lại
          </button>
        </div>
      </div>
      <p className="muted">
        {rows.length} bài làm · {scored.length} đã nộp · điểm trung bình {avg}
      </p>
      <table>
        <thead>
          <tr>
            <th>Tài khoản</th>
            <th>Họ tên</th>
            <th>Điểm</th>
            <th>Nộp lúc</th>
            <th>Tự thu</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.user_id}>
              <td>{r.username}</td>
              <td>{r.full_name}</td>
              <td>{r.score ?? "–"}</td>
              <td>{r.submitted_at ? new Date(r.submitted_at).toLocaleString("vi-VN") : "Đang làm"}</td>
              <td>{r.auto_submitted ? "Có" : ""}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
