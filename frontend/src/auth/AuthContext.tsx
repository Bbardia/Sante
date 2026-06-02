import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { login as apiLogin, getMe, tokenStore, type User } from "../api/client";

interface AuthContextValue {
  user: User | null;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const queryClient = useQueryClient();

  // Restore session from stored token on mount
  useEffect(() => {
    const token = tokenStore.get();
    if (!token) return;
    getMe()
      .then(setUser)
      .catch(() => {
        tokenStore.clear();
        setUser(null);
      });
  }, []);

  async function login(username: string, password: string) {
    const res = await apiLogin(username, password);
    tokenStore.set(res.access_token);
    const me = await getMe();
    setUser(me);
  }

  function logout() {
    tokenStore.clear();
    setUser(null);
    queryClient.clear();
  }

  return (
    <AuthContext.Provider value={{ user, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}
