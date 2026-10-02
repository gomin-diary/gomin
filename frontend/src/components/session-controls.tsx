"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useRef, useState } from "react";
import { useAuth } from "@/providers/auth-provider";

export function SessionControls() {
  const { member, logout } = useAuth();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const pending = useRef(false);
  const router = useRouter();
  if (member === undefined) return null;
  if (!member) return <div className="session-controls"><Link href="/login">로그인</Link></div>;
  async function signOut() {
    if (pending.current) return;
    pending.current = true;
    setBusy(true);
    setError("");
    try { await logout(); router.replace("/"); }
    catch { setError("로그아웃에 실패했어요. 다시 시도해 주세요."); }
    finally { pending.current = false; setBusy(false); }
  }
  return <div className="session-controls">
    <span>{member.name}님</span>
    <button type="button" disabled={busy} onClick={() => void signOut()}>{busy ? "로그아웃 중…" : "로그아웃"}</button>
    {error ? <span role="alert">{error}</span> : null}
  </div>;
}
