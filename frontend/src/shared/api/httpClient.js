import { tokenStore } from "./tokenStore.js";

const BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";
export const WS_BASE = BASE.replace(/^http/, "ws");

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

let unauthorizedHandler = null;
/** AuthProvider đăng ký hàm này để tự đăng xuất khi token hết hạn (401 trên request đã đăng nhập). */
export const setUnauthorizedHandler = (fn) => {
  unauthorizedHandler = fn;
};

function errorMessage(detail) {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) return detail.map((d) => d.msg).join("; "); // lỗi 422 của Pydantic
  return "Có lỗi xảy ra";
}

/**
 * Mọi lời gọi API đi qua đây. Không biết gì về nghiệp vụ.
 * options: { method, json, form, blob, auth = true }
 */
export async function request(path, { method = "GET", json, form, blob = false, auth = true } = {}) {
  const headers = {};
  const token = auth ? tokenStore.token : null;
  if (token) headers.Authorization = `Bearer ${token}`;

  let body;
  if (json !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(json);
  } else if (form) {
    body = new URLSearchParams(form); // OAuth2PasswordRequestForm cần form-urlencoded
  }

  const res = await fetch(BASE + path, { method, headers, body });
  if (!res.ok) {
    let detail;
    try {
      detail = (await res.json()).detail;
    } catch {
      /* không có body JSON */
    }
    if (res.status === 401 && token && unauthorizedHandler) unauthorizedHandler();
    throw new ApiError(errorMessage(detail), res.status);
  }
  if (res.status === 204) return null;
  return blob ? res.blob() : res.json();
}
