const BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";
export const WS_BASE = BASE.replace(/^http/, "ws");

export const session = {
  get token() {
    return localStorage.getItem("token");
  },
  get user() {
    try {
      return JSON.parse(localStorage.getItem("user"));
    } catch {
      return null;
    }
  },
  save(token, user) {
    localStorage.setItem("token", token);
    localStorage.setItem("user", JSON.stringify(user));
  },
  clear() {
    localStorage.removeItem("token");
    localStorage.removeItem("user");
  },
};

function errorMessage(detail) {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) return detail.map((d) => d.msg).join("; "); // lỗi 422 của Pydantic
  return "Có lỗi xảy ra";
}

/** Mọi lời gọi API đi qua đây: tự gắn Bearer token, tự đổi lỗi thành Error có thông báo tiếng Việt. */
export async function api(path, { method = "GET", json, form, blob = false } = {}) {
  const headers = {};
  if (session.token) headers.Authorization = `Bearer ${session.token}`;
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
    const err = new Error(errorMessage(detail));
    err.status = res.status;
    throw err;
  }
  if (res.status === 204) return null;
  return blob ? res.blob() : res.json();
}

export const login = (username, password) => api("/api/auth/login", { method: "POST", form: { username, password } });
export const register = (username, password, full_name) =>
  api("/api/auth/register", { method: "POST", json: { username, password, full_name } });
