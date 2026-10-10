import { useEffect, useState } from "react";
import { api } from "../api.js";

export default function Result({ attemptId, go }) {
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    // Nếu server vừa tự thu bài, kết quả có thể chưa sẵn sàng trong tích tắc: thử lại vài lần.
    let tries = 0;
    const load = () =>
      api(`/api/attempts/${attemptId}/result`)
        .then(setResult)
        .catch((err) => {
          if (err.status === 409 && tries++ < 5) setTimeout(load, 1000);
          else setError(err.message);
        });
    load();
  }, [attemptId]);

  if (error) return <p className="error">{error}</p>;
  if (!result) return <p>Đang tải kết quả...</p>;

  return (
    <div className="card result">
      <h1>Kết quả</h1>
      <p className="score">{result.score.toFixed(2)} / 10</p>
      <p>
        Đúng {result.correct}/{result.total} câu
      </p>
      {result.auto_submitted && <p className="muted">Bài được hệ thống tự động thu khi hết giờ.</p>}
      <p className="muted">Nộp lúc {new Date(result.submitted_at).toLocaleString("vi-VN")}</p>
      <button onClick={() => go("exams")}>Về danh sách đề</button>
    </div>
  );
}
