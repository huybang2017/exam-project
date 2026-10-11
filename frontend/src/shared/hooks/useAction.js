import { useCallback, useState } from "react";

/**
 * Bọc một thao tác ghi (đăng nhập, công bố đề, ...) để có sẵn trạng thái loading/error.
 * run(...args) trả về kết quả, hoặc undefined nếu lỗi (lỗi nằm ở `error`).
 */
export function useAction(fn) {
  const [state, setState] = useState({ loading: false, error: null });

  const run = useCallback(
    async (...args) => {
      setState({ loading: true, error: null });
      try {
        const result = await fn(...args);
        setState({ loading: false, error: null });
        return result;
      } catch (error) {
        setState({ loading: false, error });
        return undefined;
      }
    },
    [fn]
  );

  const reset = useCallback(() => setState({ loading: false, error: null }), []);
  return { run, reset, ...state };
}
