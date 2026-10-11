import { Badge, Card } from "../../shared/ui";
import { formatDateTime } from "../../shared/lib/format.js";
import { WINDOW_LABEL, WINDOW_TONE, windowState } from "./examStatus.js";

/**
 * Thẻ một đề thi, dùng cho mọi vai trò. Điểm khác nhau nằm ở slot:
 * - actions: các nút hành động (do nơi dùng quyết định theo vai trò)
 * - extraMeta: thông tin thêm sau dòng mô tả (vd. "Đã công bố" cho giáo viên)
 */
export default function ExamCard({ exam, actions, extraMeta }) {
  const state = windowState(exam);
  return (
    <Card
      title={exam.title}
      actions={<Badge tone={WINDOW_TONE[state]}>{WINDOW_LABEL[state]}</Badge>}
      footer={actions}
    >
      <p className="muted">
        {exam.question_count} câu · {exam.duration_minutes} phút · {formatDateTime(exam.start_time)} →{" "}
        {formatDateTime(exam.end_time)}
        {extraMeta}
      </p>
    </Card>
  );
}
