import styles from "./ChoiceGroup.module.css";

/**
 * Nhóm lựa chọn một (radio). options: [{ value, label }]. Dùng cho câu hỏi trắc nghiệm
 * và mọi chỗ cần chọn một trong nhiều.
 */
export default function ChoiceGroup({ name, options, value, onChange, disabled = false, legend }) {
  return (
    <fieldset className={styles.group} disabled={disabled}>
      {legend && <legend className={styles.legend}>{legend}</legend>}
      {options.map((opt) => (
        <label className={styles.option} key={opt.value}>
          <input type="radio" name={name} checked={value === opt.value} onChange={() => onChange(opt.value)} />
          {opt.label}
        </label>
      ))}
    </fieldset>
  );
}
