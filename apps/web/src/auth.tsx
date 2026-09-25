import { createContext, useContext, useEffect, useState } from "react";
import { api, Circle, getToken, setToken } from "./api";

type AuthCtx = {
  user: any | null;
  circle: Circle | null;
  role: string;
  loading: boolean;
  refresh: () => Promise<void>;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, name: string, password: string) => Promise<void>;
  join: (code: string, role: string) => Promise<void>;
  createCircle: (data: any) => Promise<void>;
  logout: () => void;
};

const Ctx = createContext<AuthCtx>(null as any);
export const useAuth = () => useContext(Ctx);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<any | null>(null);
  const [circle, setCircle] = useState<Circle | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = async () => {
    if (!getToken()) { setUser(null); setCircle(null); setLoading(false); return; }
    try {
      const me = await api.me();
      setUser(me);
      const circles = await api.circles();
      setCircle(circles[0] ?? null);
    } catch { /* handled by api 401 redirect */ }
    setLoading(false);
  };

  useEffect(() => { refresh(); }, []);

  const login = async (email: string, password: string) => {
    const r = await api.login(email, password);
    setToken(r.token);
    await refresh();
  };
  const register = async (email: string, name: string, password: string) => {
    const r = await api.register(email, name, password);
    setToken(r.token);
    await refresh();
  };
  const join = async (code: string, role: string) => { await api.joinCircle(code, role); await refresh(); };
  const createCircle = async (data: any) => { await api.createCircle(data); await refresh(); };
  const logout = () => { setToken(null); setUser(null); setCircle(null); };

  const role = circle?.my_role ?? circle?.members?.find((m) => m.user_id === user?.id)?.role ?? "member";
  return (
    <Ctx.Provider value={{ user, circle, role, loading, refresh, login, register, join, createCircle, logout }}>
      {children}
    </Ctx.Provider>
  );
}
