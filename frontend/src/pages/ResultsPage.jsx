import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { resultsApi } from "../features/results/resultsApi.js";
import ScoreTable from "../features/results/ScoreTable.jsx";
import { summarizeResults } from "../features/results/summarizeResults.js";
import { useExamResults } from "../features/results/useExamResults.js";
import { Alert, AsyncBoundary, Button, DownloadButton, PageHeader } from "../shared/ui";

export default function ResultsPage() {
  const { examId } = useParams();
  const { rows, loading, error, reload } = useExamResults(examId);
  const [downloadError, setDownloadError] = useState(null);
  const summary = summarizeResults(rows);

  return (
    <>
      <PageHeader
        title={`Bảng điểm đề #${examId}`}
        subtitle={`${summary.total} bài làm · ${summary.submitted} đã nộp · điểm trung bình ${summary.average}`}
        actions={
          <>
            <DownloadButton
              fetcher={() => resultsApi.downloadCsv(examId)}
              filename={`exam_${examId}_results.csv`}
              onError={setDownloadError}
            >
              Tải CSV
            </DownloadButton>
            <Button as={Link} to="/" variant="secondary">
              Quay lại
            </Button>
          </>
        }
      />
      {downloadError && <Alert onClose={() => setDownloadError(null)}>{downloadError.message}</Alert>}
      <AsyncBoundary loading={loading} error={error} onRetry={reload}>
        <ScoreTable rows={rows} />
      </AsyncBoundary>
    </>
  );
}
