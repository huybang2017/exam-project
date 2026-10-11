import { request } from "../../shared/api/httpClient.js";

export const attemptsApi = {
  list: () => request("/api/attempts"),
  start: (examId) => request(`/api/exams/${examId}/attempts`, { method: "POST" }),
  saveAnswers: (attemptId, answers) =>
    request(`/api/attempts/${attemptId}/answers`, { method: "PUT", json: { answers } }),
  submit: (attemptId) => request(`/api/attempts/${attemptId}/submit`, { method: "POST" }),
  result: (attemptId) => request(`/api/attempts/${attemptId}/result`),
};
