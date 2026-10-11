import { EmptyState } from "../../shared/ui";
import ExamCard from "./ExamCard.jsx";

/**
 * Danh sách đề thi tổng quát. Quyết định hành động và thông tin phụ nhận qua render-prop nên cùng một
 * component phục vụ sinh viên và giáo viên:
 *   <ExamList exams={...} renderActions={(exam) => <.../>} renderMeta={(exam) => "..."} />
 */
export default function ExamList({ exams, renderActions, renderMeta, emptyText = "Chưa có đề thi nào." }) {
  if (exams.length === 0) return <EmptyState title={emptyText} />;
  return exams.map((exam) => (
    <ExamCard key={exam.id} exam={exam} actions={renderActions?.(exam)} extraMeta={renderMeta?.(exam)} />
  ));
}
