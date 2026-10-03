"use client";

import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from "react";
import { usePathname } from "next/navigation";
import { apiFetch, ApiRequestError } from "@/lib/api";

export type Member = { id: string; email: string; name: string };
type AuthContextValue = {
  member: Member | null | undefined;
  error: string;
  refresh: () => Promise<void>;
  acceptLogin: (member: Member) => void;
  logout: () => Promise<void>;
};
const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [member, setMember] = useState<Member | null>();
  const [error, setError] = useState("");
  const version = useRef(0);
  const pathname = usePathname();
  const refresh = useCallback(async () => {
    const current = ++version.current;
    try {
      const result = await apiFetch<Member>("/api/v1/auth/me");
      if (current !== version.current) return;
      setMember(result);
      setError("");
    } catch (cause) {
      if (current !== version.current) return;
      if (cause instanceof ApiRequestError && cause.status === 401) {
        setMember(null);
        setError("");
      } else {
        setMember(undefined);
        setError("로그인 상태를 확인할 수 없어요. 연결을 확인하고 다시 시도해 주세요.");
      }
    }
  }, []);
  const acceptLogin = useCallback((value: Member) => {
    ++version.current;
    setMember(value);
    setError("");
  }, []);
  const logout = useCallback(async () => {
    ++version.current;
    await apiFetch<null>("/api/v1/auth/logout", { method: "POST" });
    ++version.current;
    // Home logout has no pathname transition to trigger a session check.
    // Protected pages wait for home navigation to avoid a login redirect race.
    setMember(pathname === "/" ? null : undefined);
    setError("");
  }, [pathname]);
  const invalidate = useCallback(() => { ++version.current; }, []);
  useEffect(() => {
    const initial = window.setTimeout(() => void refresh(), 0);
    const check = () => { if (document.visibilityState === "visible") void refresh(); };
    window.addEventListener("focus", check);
    document.addEventListener("visibilitychange", check);
    // Check expiration on return to a page, navigation, and while using the app.
    const timer = window.setInterval(check, 5 * 60 * 1000);
    return () => {
      invalidate();
      window.clearTimeout(initial);
      window.removeEventListener("focus", check);
      document.removeEventListener("visibilitychange", check);
      window.clearInterval(timer);
    };
  }, [pathname, refresh, invalidate]);
  return <AuthContext.Provider value={{ member, error, refresh, acceptLogin, logout }}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) throw new Error("AuthProvider is required");
  return value;
}
