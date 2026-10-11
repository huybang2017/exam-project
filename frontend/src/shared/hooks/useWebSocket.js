import { useEffect, useRef } from "react";

/**
 * Mở WebSocket khi `url` có giá trị, đóng khi url đổi/unmount.
 * onMessage nhận dữ liệu đã JSON.parse.
 */
export function useWebSocket(url, onMessage) {
  const handlerRef = useRef(onMessage);
  handlerRef.current = onMessage;

  useEffect(() => {
    if (!url) return undefined;
    const ws = new WebSocket(url);
    ws.onmessage = (ev) => handlerRef.current(JSON.parse(ev.data));
    return () => ws.close();
  }, [url]);
}
