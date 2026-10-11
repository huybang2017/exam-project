import { useState } from "react";
import Button from "../Button/Button.jsx";

/**
 * Nút tải file. fetcher: () => Promise<Blob>. Dùng fetch (có header Authorization) thay vì thẻ <a>.
 * onError(error) để trang quyết định hiển thị lỗi.
 */
export default function DownloadButton({ fetcher, filename, onError, children = "Tải xuống", ...buttonProps }) {
  const [loading, setLoading] = useState(false);

  async function download() {
    setLoading(true);
    try {
      const url = URL.createObjectURL(await fetcher());
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      a.click();
      URL.revokeObjectURL(url);
    } catch (error) {
      onError?.(error);
    } finally {
      setLoading(false);
    }
  }

  return (
    <Button loading={loading} onClick={download} {...buttonProps}>
      {children}
    </Button>
  );
}
