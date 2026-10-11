import { Link } from "react-router-dom";
import { useAction } from "../../shared/hooks/useAction.js";
import { Button } from "../../shared/ui";
import { examsApi } from "./examsApi.js";

/** Nút hành động của giáo viên/admin trên một đề: Công bố (nếu còn là bản nháp) và Bảng điểm. */
export default function TeacherExamActions({ exam, onChanged, onError }) {
  const { run: publish, loading } = useAction(async () => {
    try {
      await examsApi.publish(exam.id);
      onChanged?.();
    } catch (error) {
      onError?.(error);
    }
  });

  return (
    <>
      {!exam.is_published && (
        <Button loading={loading} onClick={publish}>
          Công bố
        </Button>
      )}
      <Button as={Link} to={`/exams/${exam.id}/results`} variant="secondary">
        Bảng điểm
      </Button>
    </>
  );
}
