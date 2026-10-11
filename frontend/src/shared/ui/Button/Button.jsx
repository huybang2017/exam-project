import { cx } from "../../lib/cx.js";
import styles from "./Button.module.css";

/**
 * Nút dùng chung.
 * - variant: "primary" | "secondary" | "danger" | "link"
 * - size: "md" | "sm"
 * - loading: khoá nút và hiện nhãn đang xử lý
 * - as: đổi thẻ gốc (vd. as={Link} to="/...")
 */
export default function Button({
  variant = "primary",
  size = "md",
  loading = false,
  disabled = false,
  as: Tag = "button",
  className,
  children,
  ...rest
}) {
  const extra = Tag === "button" ? { type: rest.type ?? "button", disabled: disabled || loading } : {};
  return (
    <Tag className={cx(styles.button, styles[variant], styles[size], className)} aria-busy={loading || undefined} {...extra} {...rest}>
      {loading ? "Đang xử lý..." : children}
    </Tag>
  );
}
