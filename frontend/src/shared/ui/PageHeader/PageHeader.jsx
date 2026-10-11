import styles from "./PageHeader.module.css";

/** Đầu trang. Slot: actions (các nút ở bên phải). */
export default function PageHeader({ title, subtitle, actions }) {
  return (
    <div className={styles.header}>
      <div>
        <h1>{title}</h1>
        {subtitle && <p className="muted">{subtitle}</p>}
      </div>
      {actions && <div className={styles.actions}>{actions}</div>}
    </div>
  );
}
