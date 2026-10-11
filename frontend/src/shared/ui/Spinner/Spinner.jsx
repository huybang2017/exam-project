import styles from "./Spinner.module.css";

export default function Spinner({ label = "Đang tải..." }) {
  return (
    <p className={styles.spinner} role="status">
      <span className={styles.dot} aria-hidden="true" /> {label}
    </p>
  );
}
