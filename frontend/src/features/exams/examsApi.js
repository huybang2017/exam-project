import { request } from "../../shared/api/httpClient.js";

export const examsApi = {
  list: () => request("/api/exams"),
  publish: (examId) => request(`/api/exams/${examId}/publish`, { method: "POST" }),
};
