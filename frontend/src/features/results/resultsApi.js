import { request } from "../../shared/api/httpClient.js";

export const resultsApi = {
  list: (examId) => request(`/api/exams/${examId}/results`),
  downloadCsv: (examId) => request(`/api/exams/${examId}/results.csv`, { blob: true }),
};
