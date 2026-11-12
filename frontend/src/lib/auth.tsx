import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { api, getToken, setToken } from "./api";
import type { User } from "./types";

interface AuthContextValue {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, name: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    const token = getToken();
    if (!token) {
      setLoading(false);
      return;
    }
    api
      .get<User>("/api/auth/me")
      .then((profile) => {
        if (active) setUser(profile);
      })
      .catch(() => {
        setToken(null);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    const onUnauthorized = () => {
      setToken(null);
      setUser(null);
    };
    window.addEventListener("nexamind:unauthorized", onUnauthorized);
    return () => window.removeEventListener("nexamind:unauthorized", onUnauthorized);
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      loading,
      async login(email, password) {
        const response = await api.post<{ access_token: string; user: User }>("/api/auth/login", { email, password });
        setToken(response.access_token);
        setUser(response.user);
      },
      async register(email, password, name) {
        const response = await api.post<{ access_token: string; user: User }>("/api/auth/register", {
          email,
          password,
          name
        });
        setToken(response.access_token);
        setUser(response.user);
      },
      logout() {
        setToken(null);
        setUser(null);
      }
    }),
    [user, loading]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside AuthProvider");
  return context;
}
