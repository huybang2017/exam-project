import { useState } from "react";
import { session } from "./api.js";
import Login from "./pages/Login.jsx";
import ExamList from "./pages/ExamList.jsx";
import TakeExam from "./pages/TakeExam.jsx";
import Result from "./pages/Result.jsx";
import Results from "./pages/Results.jsx";

const ROLE_LABEL = { admin: "Admin", teacher: "Giáo viên", student: "Sinh viên" };

export default function App() {
  const [user, setUser] = useState(session.user);
  // Điều hướng đơn giản bằng state: { page, ...tham số }
  const [view, setView] = useState({ page: "exams" });

  if (!user || !session.token) {
    return <Login onLoggedIn={setUser} />;
  }

  const logout = () => {
    session.clear();
    setUser(null);
    setView({ page: "exams" });
  };
  const go = (page, params = {}) => setView({ page, ...params });

  return (
    <div className="app">
      <header className="topbar">
        <strong onClick={() => go("exams")} style={{ cursor: "pointer" }}>
          Thi trực tuyến
        </strong>
        <span>
          {user.full_name} <em>({ROLE_LABEL[user.role]})</em>
          <button className="link" onClick={logout}>
            Đăng xuất
          </button>
        </span>
      </header>
      <main>
        {view.page === "exams" && <ExamList user={user} go={go} />}
        {view.page === "take" && <TakeExam examId={view.examId} go={go} />}
        {view.page === "result" && <Result attemptId={view.attemptId} go={go} />}
        {view.page === "results" && <Results examId={view.examId} go={go} />}
      </main>
    </div>
  );
}
