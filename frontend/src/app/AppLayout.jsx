import { Link, Outlet } from "react-router-dom";
import { ROLE_LABEL, useAuth } from "../features/auth/AuthContext.jsx";
import { Button } from "../shared/ui";
import styles from "./AppLayout.module.css";

/** Khung chung cho các trang sau đăng nhập: thanh trên cùng + vùng nội dung (<Outlet />). */
export default function AppLayout() {
  const { user, logout } = useAuth();
  return (
    <div>
      <header className={styles.topbar}>
        <Link to="/" className={styles.brand}>
          Thi trực tuyến
        </Link>
        <span>
          {user.full_name} <em>({ROLE_LABEL[user.role]})</em>
          <Button variant="link" onClick={logout}>
            Đăng xuất
          </Button>
        </span>
      </header>
      <main className={styles.main}>
        <Outlet />
      </main>
    </div>
  );
}
