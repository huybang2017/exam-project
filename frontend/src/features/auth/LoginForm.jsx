import { useState } from "react";
import { useAction } from "../../shared/hooks/useAction.js";
import { Alert, Button, TextInput } from "../../shared/ui";
import { useAuth } from "./AuthContext.jsx";

export default function LoginForm({ onSuccess }) {
  const { login } = useAuth();
  const [form, setForm] = useState({ username: "", password: "" });
  const { run, loading, error } = useAction(login);
  const set = (key) => (e) => setForm({ ...form, [key]: e.target.value });

  async function submit(e) {
    e.preventDefault();
    const user = await run(form.username, form.password);
    if (user) onSuccess?.(user);
  }

  return (
    <form onSubmit={submit}>
      <TextInput label="Tên đăng nhập" value={form.username} onChange={set("username")} autoFocus required minLength={3} />
      <TextInput label="Mật khẩu" type="password" value={form.password} onChange={set("password")} required minLength={6} />
      {error && <Alert>{error.message}</Alert>}
      <Button type="submit" loading={loading}>
        Đăng nhập
      </Button>
    </form>
  );
}
