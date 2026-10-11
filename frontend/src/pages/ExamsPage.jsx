import { useState } from "react";
import { useAuth } from "../features/auth/AuthContext.jsx";
import { useMyAttempts } from "../features/attempts/useMyAttempts.js";
import ExamList from "../features/exams/ExamList.jsx";
import StudentExamActions from "../features/exams/StudentExamActions.jsx";
import TeacherExamActions from "../features/exams/TeacherExamActions.jsx";
import { useExams } from "../features/exams/useExams.js";
import { Alert, AsyncBoundary, PageHeader } from "../shared/ui";

/** Trang chủ: cùng một ExamList, khác nhau ở hành động theo vai trò. */
export default function ExamsPage() {
  const { user } = useAuth();
  const isStudent = user.role === "student";
  const exams = useExams();
  const attempts = useMyAttempts({ enabled: isStudent });
  const [actionError, setActionError] = useState(null);

  return (
    <>
      <PageHeader title={isStudent ? "Đề thi dành cho bạn" : "Đề thi của tôi"} />
      {actionError && <Alert onClose={() => setActionError(null)}>{actionError.message}</Alert>}
      <AsyncBoundary
        loading={exams.loading || attempts.loading}
        error={exams.error || attempts.error}
        onRetry={() => {
          exams.reload();
          attempts.reload();
        }}
      >
        <ExamList
          exams={exams.exams}
          renderMeta={isStudent ? undefined : (exam) => (exam.is_published ? " · Đã công bố" : " · Bản nháp")}
          renderActions={(exam) =>
            isStudent ? (
              <StudentExamActions exam={exam} attempt={attempts.byExam[exam.id]} />
            ) : (
              <TeacherExamActions exam={exam} onChanged={exams.reload} onError={setActionError} />
            )
          }
        />
      </AsyncBoundary>
    </>
  );
}
