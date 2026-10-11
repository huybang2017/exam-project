import { useAsync } from "../../shared/hooks/useAsync.js";
import { resultsApi } from "./resultsApi.js";

export function useExamResults(examId) {
  const { data, error, loading, reload } = useAsync(() => resultsApi.list(examId), [examId]);
  return { rows: data ?? [], error, loading, reload };
}
