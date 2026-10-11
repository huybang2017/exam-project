import { Link, useParams } from "react-router-dom";
import { useAttemptResult } from "../features/attempts/useAttemptResult.js";
import ResultSummary from "../features/attempts/ResultSummary.jsx";
import { AsyncBoundary, Button } from "../shared/ui";

export default function ResultPage() {
  const { attemptId } = useParams();
  const { data: result, loading, error } = useAttemptResult(attemptId);

  return (
    <AsyncBoundary loading={loading} error={error} loadingLabel="Đang tải kết quả...">
      {result && (
        <ResultSummary
          result={result}
          actions={
            <Button as={Link} to="/">
              Về danh sách đề
            </Button>
          }
        />
      )}
    </AsyncBoundary>
  );
}
