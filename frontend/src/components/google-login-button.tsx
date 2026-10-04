"use client";
import Image from "next/image";
import { useRef, useState } from "react";
import { apiFetch, ApiRequestError } from "@/lib/api";
import { browserRoutingStorage, googleAuthorizationUrl, saveGoogleContext } from "@/lib/google-oauth";
import styles from "./auth-page.module.css";

export function GoogleLoginButton({ origin, disabled = false }: { origin: "/login" | "/signup"; disabled?: boolean }) {
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const pending = useRef(false);
  async function begin() {
    if (pending.current) return;
    pending.current = true; setBusy(true); setNotice("");
    try {
      const result = await apiFetch<{ authorization_url: string }>("/api/v1/auth/google/start?response=json");
      const url = googleAuthorizationUrl(result.authorization_url);
      saveGoogleContext(browserRoutingStorage(), origin, new URLSearchParams(window.location.search).get("next"));
      window.location.assign(url);
    } catch (error) {
      setNotice(error instanceof ApiRequestError ? error.message : "Google 로그인을 시작할 수 없어요. 다시 시도해 주세요.");
      pending.current = false; setBusy(false);
    }
  }
  return <>
    <button type="button" className={styles.googleButton} onClick={begin} disabled={disabled || busy}>
      <Image src="/images/auth/google.svg" width={24} height={24} alt="" />
      {busy ? "Google로 이동 중…" : "Google로 계속하기"}
    </button>
    {notice ? <p className={styles.error} role="alert">{notice}</p> : null}
  </>;
}
