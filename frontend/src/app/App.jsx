import { Navigate, Route, Routes } from "react-router-dom";
import ExamsPage from "../pages/ExamsPage.jsx";
import LoginPage from "../pages/LoginPage.jsx";
import ResultPage from "../pages/ResultPage.jsx";
import ResultsPage from "../pages/ResultsPage.jsx";
import TakeExamPage from "../pages/TakeExamPage.jsx";
import AppLayout from "./AppLayout.jsx";
import ProtectedRoute from "./ProtectedRoute.jsx";

const TEACHING_ROLES = ["teacher", "admin"];

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />

      <Route element={<ProtectedRoute />}>
        <Route element={<AppLayout />}>
          <Route index element={<ExamsPage />} />
          <Route path="attempts/:attemptId/result" element={<ResultPage />} />

          <Route element={<ProtectedRoute roles={["student"]} />}>
            <Route path="exams/:examId/take" element={<TakeExamPage />} />
          </Route>

          <Route element={<ProtectedRoute roles={TEACHING_ROLES} />}>
            <Route path="exams/:examId/results" element={<ResultsPage />} />
          </Route>
        </Route>
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
