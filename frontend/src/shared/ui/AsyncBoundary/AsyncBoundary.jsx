import Alert from "../Alert/Alert.jsx";
import Button from "../Button/Button.jsx";
import EmptyState from "../EmptyState/EmptyState.jsx";
import Spinner from "../Spinner/Spinner.jsx";

/**
 * Gom ba trạng thái tải dữ liệu: đang tải / lỗi / rỗng, rồi mới render children.
 * Dùng chung cho mọi trang lấy dữ liệu: <AsyncBoundary loading error isEmpty onRetry>...</AsyncBoundary>
 */
export default function AsyncBoundary({ loading, error, isEmpty = false, emptyTitle, emptyDescription, onRetry, loadingLabel, children }) {
  if (loading) return <Spinner label={loadingLabel} />;
  if (error) {
    return (
      <Alert tone="danger">
        {error.message}
        {onRetry && (
          <Button variant="link" size="sm" onClick={onRetry}>
            Thử lại
          </Button>
        )}
      </Alert>
    );
  }
  if (isEmpty) return <EmptyState title={emptyTitle} description={emptyDescription} />;
  return children;
}
