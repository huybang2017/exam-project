import { useAsync } from "../../shared/hooks/useAsync.js";
import { attemptsApi } from "./attemptsApi.js";

const RETRIES = 5;
const RETRY_DELAY_MS = 1000;

/**
 * Kết quả một bài làm. Nếu server vừa tự thu bài thì kết quả có thể chưa sẵn sàng trong tích tắc
 * (409 "Bài chưa được nộp"): thử lại vài lần trước khi báo lỗi.
 */
export function useAttemptResult(attemptId) {
  return useAsync(async () => {
    for (let attempt = 0; ; attempt++) {
      try {
        return await attemptsApi.result(attemptId);
      } catch (err) {
        if (err.status !== 409 || attempt >= RETRIES) throw err;
        await new Promise((resolve) => setTimeout(resolve, RETRY_DELAY_MS));
      }
    }
  }, [attemptId]);
}
