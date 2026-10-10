import { useState } from "react";
import { login, register, session } from "../api.js";

export default function Login({ onLoggedIn }) {
  const [mode, setMode] = useState("login"); // login | register
  const [form, setForm] = useState({ username: "", password: "", full_name: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  async function submit(e) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      if (mode === "register") {
        await register(form.username, form.password, form.full_name);
      }
      const res = await login(form.username, form.password);
      session.save(res.access_token, res.user);
      onLoggedIn(res.user);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="card login">
      <h1>{mode === "login" ? "Đăng nhập" : "Đăng ký sinh viên"}</h1>
      <form onSubmit={submit}>
        <label>
          Tên đăng nhập
          <input value={form.username} onChange={set("username")} autoFocus required minLength={3} />
        </label>
        {mode === "register" && (
          <label>
            Họ và tên
            <input value={form.full_name} onChange={set("full_name")} required />
          </label>
        )}
        <label>
          Mật khẩu
          <input type="password" value={form.password} onChange={set("password")} required minLength={6} />
        </label>
        {error && <p className="error">{error}</p>}
        <button disabled={busy}>{busy ? "Đang xử lý..." : mode === "login" ? "Đăng nhập" : "Đăng ký và đăng nhập"}</button>
      </form>
      <p>
        {mode === "login" ? "Chưa có tài khoản?" : "Đã có tài khoản?"}{" "}
        <button className="link" onClick={() => setMode(mode === "login" ? "register" : "login")}>
          {mode === "login" ? "Đăng ký" : "Đăng nhập"}
        </button>
      </p>
    </div>
  );
}
