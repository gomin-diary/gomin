"use client";

import { createContext, useCallback, useContext, useEffect, useRef, useState, useSyncExternalStore, type ReactNode } from "react";
import { usePathname } from "next/navigation";
import { apiFetch, ApiRequestError, subscribeAuthFailure } from "@/lib/api";
import { createAuthSession, type Member } from "@/lib/auth-session";

export type { Member } from "@/lib/auth-session";
type AuthContextValue = {
  member: Member | null | undefined;
  error: string;
  refresh: () => Promise<void>;
  acceptLogin: (member: Member) => void;
  logout: () => Promise<void>;
};
const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session] = useState(() => createAuthSession(
    () => apiFetch<Member>("/api/v1/auth/me"),
    (error) => error instanceof ApiRequestError && error.status === 401,
  ));
  const { member, error } = useSyncExternalStore(session.subscribe, session.getSnapshot, session.getServerSnapshot);
  const pathname = usePathname();
  const loggedOut = useRef(false);
  const acceptLogin = useCallback((value: Member) => {
    loggedOut.current = false;
    session.accept(value);
  }, [session]);
  const logout = useCallback(async () => {
    session.invalidate();
    await apiFetch<null>("/api/v1/auth/logout", { method: "POST" });
    loggedOut.current = true;
    // Hide protected content until guide navigation to avoid an AuthGuard race.
    session.accept(pathname === "/guide" ? null : undefined);
  }, [pathname, session]);
  useEffect(() => {
    if (loggedOut.current && pathname === "/guide") {
      loggedOut.current = false;
      session.accept(null);
    }
  }, [pathname, session]);
  useEffect(() => {
    const unsubscribe = subscribeAuthFailure(session.captureUnauthorized);
    const initial = window.setTimeout(() => void session.recheck(), 0);
    const check = () => { if (document.visibilityState === "visible") void session.recheck(); };
    window.addEventListener("focus", check);
    document.addEventListener("visibilitychange", check);
    return () => {
      unsubscribe();
      session.invalidate();
      window.clearTimeout(initial);
      window.removeEventListener("focus", check);
      document.removeEventListener("visibilitychange", check);
    };
  }, [session]);
  return <AuthContext.Provider value={{ member, error, refresh: session.refresh, acceptLogin, logout }}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) throw new Error("AuthProvider is required");
  return value;
}
