import { Card } from "../../shared/ui";
import { formatDateTime } from "../../shared/lib/format.js";
import styles from "./ResultSummary.module.css";

/** Tóm tắt kết quả một bài làm. Slot: actions (vd. nút "Về danh sách đề"). */
export default function ResultSummary({ result, actions }) {
  return (
    <Card title="Kết quả" className={styles.summary} footer={actions}>
      <p className={styles.score}>{result.score.toFixed(2)} / 10</p>
      <p>
        Đúng {result.correct}/{result.total} câu
      </p>
      {result.auto_submitted && <p className="muted">Bài được hệ thống tự động thu khi hết giờ.</p>}
      <p className="muted">Nộp lúc {formatDateTime(result.submitted_at)}</p>
    </Card>
  );
}
