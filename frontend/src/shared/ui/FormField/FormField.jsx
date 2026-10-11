import { useId } from "react";
import { cx } from "../../lib/cx.js";
import styles from "./FormField.module.css";

/** Khung nhãn + thông báo lỗi/gợi ý bọc quanh một ô nhập bất kỳ (render-prop nhận id để nối label). */
export function FormField({ label, error, hint, children }) {
  const id = useId();
  return (
    <div className={styles.field}>
      {label && <label htmlFor={id}>{label}</label>}
      {children(id)}
      {hint && !error && <span className="muted">{hint}</span>}
      {error && <span className={styles.error}>{error}</span>}
    </div>
  );
}

/** Ô nhập một dòng: <TextInput label="Tên đăng nhập" value={v} onChange={...} error={...} />. */
export default function TextInput({ label, error, hint, className, ...inputProps }) {
  return (
    <FormField label={label} error={error} hint={hint}>
      {(id) => <input id={id} className={cx(styles.input, error && styles.invalid, className)} {...inputProps} />}
    </FormField>
  );
}
