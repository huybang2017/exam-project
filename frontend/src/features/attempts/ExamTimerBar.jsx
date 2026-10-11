import { formatMmSs } from "../../shared/lib/format.js";
import { cx } from "../../shared/lib/cx.js";
import styles from "./ExamTimerBar.module.css";

const DANGER_BELOW_SECONDS = 60;

/** Thanh trạng thái khi làm bài: tiến độ, đồng hồ đếm ngược, trạng thái lưu. */
export default function ExamTimerBar({ answered, total, remaining, saveState }) {
  const danger = remaining !== null && remaining < DANGER_BELOW_SECONDS;
  return (
    <div className={styles.bar}>
      <span>
        Đã làm {answered}/{total}
      </span>
      <span className={cx(styles.clock, danger && styles.danger)}>{remaining === null ? "--:--" : formatMmSs(remaining)}</span>
      <span className="muted">{saveState}</span>
    </div>
  );
}
