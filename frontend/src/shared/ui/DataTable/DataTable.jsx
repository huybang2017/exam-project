import EmptyState from "../EmptyState/EmptyState.jsx";
import styles from "./DataTable.module.css";

/**
 * Bảng dữ liệu điều khiển bằng cấu hình cột.
 * columns: [{ key, header, render?: (row) => node, align?: "left" | "right" | "center" }]
 * Không có render thì hiển thị row[key] ("–" khi null/rỗng).
 */
export default function DataTable({ columns, rows, getRowKey, emptyText = "Không có dữ liệu" }) {
  if (rows.length === 0) return <EmptyState title={emptyText} />;
  return (
    <table className={styles.table}>
      <thead>
        <tr>
          {columns.map((c) => (
            <th key={c.key} style={{ textAlign: c.align }}>
              {c.header}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => (
          <tr key={getRowKey(row)}>
            {columns.map((c) => (
              <td key={c.key} style={{ textAlign: c.align }}>
                {c.render ? c.render(row) : (row[c.key] ?? "–")}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}
