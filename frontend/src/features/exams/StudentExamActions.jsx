import { Link } from "react-router-dom";
import { Button } from "../../shared/ui";
import { STUDENT_ACTION, STUDENT_ACTION_LABEL, studentAction } from "./examStatus.js";

/** Nút hành động của sinh viên trên một đề: Làm bài / Tiếp tục làm bài / Xem kết quả. */
export default function StudentExamActions({ exam, attempt }) {
  const action = studentAction(exam, attempt);
  const to =
    action.type === STUDENT_ACTION.RESULT ? `/attempts/${attempt.id}/result` : `/exams/${exam.id}/take`;

  if (action.disabled) {
    return <Button disabled>{STUDENT_ACTION_LABEL[action.type]}</Button>;
  }
  return (
    <Button as={Link} to={to}>
      {STUDENT_ACTION_LABEL[action.type]}
    </Button>
  );
}
