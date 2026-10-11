import Button from "../Button/Button.jsx";
import styles from "./ConfirmDialog.module.css";

/** Hộp thoại xác nhận (thay window.confirm). tone="danger" đổi nút xác nhận sang màu đỏ. */
export default function ConfirmDialog({
  open,
  title,
  message,
  confirmLabel = "Xác nhận",
  cancelLabel = "Huỷ",
  tone = "primary",
  loading = false,
  onConfirm,
  onCancel,
}) {
  if (!open) return null;
  return (
    <div className={styles.overlay} onClick={onCancel}>
      <div className={styles.dialog} role="dialog" aria-modal="true" aria-label={title} onClick={(e) => e.stopPropagation()}>
        <h2>{title}</h2>
        {message && <p className="muted">{message}</p>}
        <div className={styles.actions}>
          <Button variant="secondary" onClick={onCancel} disabled={loading}>
            {cancelLabel}
          </Button>
          <Button variant={tone} onClick={onConfirm} loading={loading}>
            {confirmLabel}
          </Button>
        </div>
      </div>
    </div>
  );
}
