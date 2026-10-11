import styles from "./EmptyState.module.css";

/** Trạng thái rỗng. Slot: action (vd. một Button). */
export default function EmptyState({ title = "Chưa có dữ liệu", description, action }) {
  return (
    <div className={styles.empty}>
      <strong>{title}</strong>
      {description && <p className="muted">{description}</p>}
      {action}
    </div>
  );
}
