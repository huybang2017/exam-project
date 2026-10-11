import { useAsync } from "../../shared/hooks/useAsync.js";
import { examsApi } from "./examsApi.js";

/** Danh sách đề phù hợp vai trò của người đăng nhập (backend tự lọc). */
export function useExams() {
  const { data, error, loading, reload } = useAsync(() => examsApi.list(), []);
  return { exams: data ?? [], error, loading, reload };
}
