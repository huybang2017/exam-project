// Quy tắc hiển thị (thuần JS, không JSX): trạng thái khung giờ và hành động phù hợp với từng vai trò.

export const WINDOW = { UPCOMING: "upcoming", OPEN: "open", CLOSED: "closed" };

export const WINDOW_LABEL = { upcoming: "Chưa mở", open: "Đang mở", closed: "Đã đóng" };
export const WINDOW_TONE = { upcoming: "warning", open: "success", closed: "neutral" };

export function windowState(exam, now = Date.now()) {
  if (now < new Date(exam.start_time)) return WINDOW.UPCOMING;
  if (now > new Date(exam.end_time)) return WINDOW.CLOSED;
  return WINDOW.OPEN;
}

export const STUDENT_ACTION = { RESULT: "result", CONTINUE: "continue", START: "start" };

/** Sinh viên làm được gì với đề này, dựa vào bài làm đã có (nếu có) và khung giờ. */
export function studentAction(exam, attempt, now = Date.now()) {
  if (attempt?.submitted) return { type: STUDENT_ACTION.RESULT, disabled: false };
  if (attempt) return { type: STUDENT_ACTION.CONTINUE, disabled: false };
  return { type: STUDENT_ACTION.START, disabled: windowState(exam, now) !== WINDOW.OPEN };
}

export const STUDENT_ACTION_LABEL = { result: "Xem kết quả", continue: "Tiếp tục làm bài", start: "Làm bài" };
