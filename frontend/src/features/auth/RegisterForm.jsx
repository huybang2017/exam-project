import { useState } from "react";
import { useAction } from "../../shared/hooks/useAction.js";
import { Alert, Button, TextInput } from "../../shared/ui";
import { useAuth } from "./AuthContext.jsx";

export default function RegisterForm({ onSuccess }) {
  const { register } = useAuth();
  const [form, setForm] = useState({ username: "", full_name: "", password: "" });
  const { run, loading, error } = useAction(register);
  const set = (key) => (e) => setForm({ ...form, [key]: e.target.value });

  async function submit(e) {
    e.preventDefault();
    const user = await run(form.username, form.password, form.full_name);
    if (user) onSuccess?.(user);
  }

  return (
    <form onSubmit={submit}>
      <TextInput label="Tên đăng nhập" value={form.username} onChange={set("username")} autoFocus required minLength={3} />
      <TextInput label="Họ và tên" value={form.full_name} onChange={set("full_name")} required />
      <TextInput label="Mật khẩu" type="password" value={form.password} onChange={set("password")} required minLength={6} />
      {error && <Alert>{error.message}</Alert>}
      <Button type="submit" loading={loading}>
        Đăng ký và đăng nhập
      </Button>
    </form>
  );
}
