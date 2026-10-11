import { useAsync } from "../../shared/hooks/useAsync.js";
import { attemptsApi } from "./attemptsApi.js";

/** Bài làm của sinh viên hiện tại, trả thêm map examId -> attempt để tra nhanh. */
export function useMyAttempts({ enabled = true } = {}) {
  const { data, error, loading, reload } = useAsync(() => (enabled ? attemptsApi.list() : Promise.resolve([])), [enabled]);
  const attempts = data ?? [];
  const byExam = Object.fromEntries(attempts.map((a) => [a.exam_id, a]));
  return { attempts, byExam, error, loading, reload };
}
