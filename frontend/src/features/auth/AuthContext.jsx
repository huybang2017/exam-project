import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { setUnauthorizedHandler } from "../../shared/api/httpClient.js";
import { tokenStore } from "../../shared/api/tokenStore.js";
import { authApi } from "./authApi.js";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(tokenStore.token ? tokenStore.user : null);

  const logout = useCallback(() => {
    tokenStore.clear();
    setUser(null);
  }, []);

  const login = useCallback(async (username, password) => {
    const res = await authApi.login(username, password);
    tokenStore.save(res.access_token, res.user);
    setUser(res.user);
    return res.user;
  }, []);

  const register = useCallback(
    async (username, password, fullName) => {
      await authApi.register(username, password, fullName);
      return login(username, password);
    },
    [login]
  );

  // Token hết hạn (401 trên request đã đăng nhập) -> tự đăng xuất, ProtectedRoute sẽ đưa về /login
  useEffect(() => {
    setUnauthorizedHandler(logout);
    return () => setUnauthorizedHandler(null);
  }, [logout]);

  const value = useMemo(() => ({ user, login, register, logout }), [user, login, register, logout]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth phải nằm trong <AuthProvider>");
  return ctx;
}

export const ROLE_LABEL = { admin: "Admin", teacher: "Giáo viên", student: "Sinh viên" };
