"use client";

import { useEffect, useRef, type ReactNode } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/providers/auth-provider";
import { useUiStore } from "@/providers/ui-store-provider";

export function AuthGuard({ children }: { children: ReactNode }) {
  const { member, error, refresh } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const showToast = useUiStore((state) => state.showToast);
  const dismissToast = useUiStore((state) => state.dismissToast);
  const notification = useRef<{ key: string; id: number } | null>(null);
  useEffect(() => {
    if (member) {
      if (notification.current) dismissToast(notification.current.id);
      notification.current = null;
      return;
    }
    const key = member === null ? "login-required" : error;
    if (key && key !== notification.current?.key) {
      const id = member === null
        ? showToast("로그인을 진행해주세요")
        : showToast(error, { label: "다시 시도", onClick: () => void refresh() });
      notification.current = { key, id };
    }
    if (member === null) router.replace(`/login?next=${encodeURIComponent(pathname)}&reason=auth`);
  }, [member, error, pathname, router, refresh, showToast, dismissToast]);
  return member ? children : null;
}
