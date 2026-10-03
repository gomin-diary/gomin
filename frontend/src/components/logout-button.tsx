"use client";

import Image from "next/image";
import { useRouter } from "next/navigation";
import { useRef, useState } from "react";
import { useAuth } from "@/providers/auth-provider";

export function LogoutButton() {
  const { logout } = useAuth();
  const router = useRouter();
  const pending = useRef(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function signOut() {
    if (pending.current) return;
    pending.current = true;
    setBusy(true);
    setError("");
    try { await logout(); router.replace("/"); }
    catch { setError("로그아웃에 실패했어요. 다시 시도해 주세요."); }
    finally { pending.current = false; setBusy(false); }
  }

  return <>
    <button className="account-action account-action--logout" type="button" disabled={busy} onClick={() => void signOut()}>
      <Image src="/images/navigation/logout.svg" width={20} height={20} alt="" />
      <span>{busy ? "로그아웃 중…" : "로그아웃"}</span>
    </button>
    {error ? <p className="account-error" role="alert">{error}</p> : null}
  </>;
}
