import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "../features/auth/AuthContext.jsx";

/**
 * Cổng bảo vệ route (dùng làm layout route): chưa đăng nhập -> /login (nhớ trang đang vào);
 * sai vai trò -> về trang chủ. roles bỏ trống = mọi người đã đăng nhập.
 */
export default function ProtectedRoute({ roles }) {
  const { user } = useAuth();
  const location = useLocation();

  if (!user) return <Navigate to="/login" replace state={{ from: location }} />;
  if (roles && !roles.includes(user.role)) return <Navigate to="/" replace />;
  return <Outlet />;
}
