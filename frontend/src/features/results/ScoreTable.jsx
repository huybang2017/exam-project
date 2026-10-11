import { Badge, DataTable } from "../../shared/ui";
import { formatDateTime } from "../../shared/lib/format.js";

// Cấu hình cột; DataTable lo phần render nên thêm/bớt cột chỉ cần sửa mảng này.
const COLUMNS = [
  { key: "username", header: "Tài khoản" },
  { key: "full_name", header: "Họ tên" },
  { key: "score", header: "Điểm", align: "right" },
  {
    key: "submitted_at",
    header: "Nộp lúc",
    render: (r) => (r.submitted_at ? formatDateTime(r.submitted_at) : "Đang làm"),
  },
  { key: "auto_submitted", header: "Tự thu", render: (r) => (r.auto_submitted ? <Badge tone="warning">Có</Badge> : "") },
];

export default function ScoreTable({ rows }) {
  return <DataTable columns={COLUMNS} rows={rows} getRowKey={(r) => r.user_id} emptyText="Chưa có bài làm nào" />;
}
