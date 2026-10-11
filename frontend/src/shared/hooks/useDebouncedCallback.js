import { useCallback, useEffect, useRef } from "react";

/**
 * Gọi fn sau `delay` ms kể từ lần call cuối. Trả về { call, flush, cancel }:
 * flush chạy fn ngay (dùng trước khi nộp bài), cancel huỷ lần chờ.
 */
export function useDebouncedCallback(fn, delay) {
  const fnRef = useRef(fn);
  fnRef.current = fn;
  const timer = useRef(null);

  const cancel = useCallback(() => {
    clearTimeout(timer.current);
    timer.current = null;
  }, []);

  const call = useCallback(
    (...args) => {
      cancel();
      timer.current = setTimeout(() => {
        timer.current = null;
        fnRef.current(...args);
      }, delay);
    },
    [delay, cancel]
  );

  const flush = useCallback(
    (...args) => {
      cancel();
      return fnRef.current(...args);
    },
    [cancel]
  );

  useEffect(() => cancel, [cancel]);
  return { call, flush, cancel };
}
