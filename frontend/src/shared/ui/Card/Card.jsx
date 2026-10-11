import { cx } from "../../lib/cx.js";
import styles from "./Card.module.css";

/** Khung nội dung. Slot: title, subtitle, actions (góc phải tiêu đề), footer. */
export default function Card({ title, subtitle, actions, footer, className, children, ...rest }) {
  return (
    <section className={cx(styles.card, className)} {...rest}>
      {(title || actions) && (
        <header className={styles.header}>
          <div>
            {title && <h2>{title}</h2>}
            {subtitle && <p className="muted">{subtitle}</p>}
          </div>
          {actions}
        </header>
      )}
      {children}
      {footer && <footer className={styles.footer}>{footer}</footer>}
    </section>
  );
}
