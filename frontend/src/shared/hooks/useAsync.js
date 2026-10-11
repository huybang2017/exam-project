import { useCallback, useEffect, useRef, useState } from "react";

/**
 * Tải dữ liệu khi mount / khi deps đổi. Trả về { data, error, loading, reload }.
 * fn: () => Promise. Bỏ qua kết quả của lần gọi cũ nếu deps đã đổi hoặc component đã unmount.
 */
export function useAsync(fn, deps = []) {
  const [state, setState] = useState({ data: null, error: null, loading: true });
  const fnRef = useRef(fn);
  fnRef.current = fn;
  const runId = useRef(0);

  const load = useCallback(() => {
    const id = ++runId.current;
    setState((s) => ({ ...s, loading: true, error: null }));
    fnRef.current().then(
      (data) => runId.current === id && setState({ data, error: null, loading: false }),
      (error) => runId.current === id && setState({ data: null, error, loading: false })
    );
  }, []);

  useEffect(() => {
    load();
    return () => {
      runId.current++; // huỷ kết quả đang chờ
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  return { ...state, reload: load };
}
