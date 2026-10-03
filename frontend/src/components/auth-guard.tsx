"use client";

import { useEffect, type ReactNode } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/providers/auth-provider";

export function AuthGuard({ children }: { children: ReactNode }) {
  const { member, error, refresh } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  useEffect(() => {
    if (member === null) router.replace(`/login?next=${encodeURIComponent(pathname)}&reason=auth`);
  }, [member, pathname, router]);
  if (!member) return <div className="auth-status" role="status">
    <p>{error || (member === null ? "로그인이 필요해요. 로그인 화면으로 이동합니다." : "로그인 상태를 확인하고 있어요.")}</p>
    {error ? <button type="button" onClick={() => void refresh()}>다시 확인</button> : null}
  </div>;
  return children;
}
