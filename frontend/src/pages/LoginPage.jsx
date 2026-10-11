import { useState } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../features/auth/AuthContext.jsx";
import LoginForm from "../features/auth/LoginForm.jsx";
import RegisterForm from "../features/auth/RegisterForm.jsx";
import { Button, Card } from "../shared/ui";
import styles from "./LoginPage.module.css";

export default function LoginPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [mode, setMode] = useState("login"); // login | register
  const goBack = () => navigate(location.state?.from?.pathname ?? "/", { replace: true });

  if (user) return <Navigate to={location.state?.from?.pathname ?? "/"} replace />;

  const isLogin = mode === "login";
  return (
    <div className={styles.wrapper}>
      <Card title={isLogin ? "Đăng nhập" : "Đăng ký sinh viên"}>
        {isLogin ? <LoginForm onSuccess={goBack} /> : <RegisterForm onSuccess={goBack} />}
        <p className="muted">
          {isLogin ? "Chưa có tài khoản?" : "Đã có tài khoản?"}
          <Button variant="link" size="sm" onClick={() => setMode(isLogin ? "register" : "login")}>
            {isLogin ? "Đăng ký" : "Đăng nhập"}
          </Button>
        </p>
      </Card>
    </div>
  );
}
