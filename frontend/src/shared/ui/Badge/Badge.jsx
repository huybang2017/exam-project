import { cx } from "../../lib/cx.js";
import styles from "./Badge.module.css";

/** Nhãn trạng thái. tone: "neutral" | "success" | "warning" | "danger" | "info". */
export default function Badge({ tone = "neutral", children, className }) {
  return <span className={cx(styles.badge, styles[tone], className)}>{children}</span>;
}
