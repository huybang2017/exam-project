import { cx } from "../../lib/cx.js";
import styles from "./Alert.module.css";

/** Thông báo trong trang. tone: "danger" | "success" | "warning" | "info"; onClose hiện nút đóng. */
export default function Alert({ tone = "danger", onClose, children, className }) {
  return (
    <div role={tone === "danger" ? "alert" : "status"} className={cx(styles.alert, styles[tone], className)}>
      <span>{children}</span>
      {onClose && (
        <button type="button" className={styles.close} onClick={onClose} aria-label="Đóng">
          ×
        </button>
      )}
    </div>
  );
}
