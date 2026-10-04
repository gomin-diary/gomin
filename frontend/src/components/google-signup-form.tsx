"use client";
import { useEffect, useRef, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { apiFetch, ApiRequestError } from "@/lib/api";
import { legalDocuments } from "@/content/legal";
import { browserRoutingStorage, clearGoogleContext, readGoogleContext, type GooglePending } from "@/lib/google-oauth";
import { useAuth, type Member } from "@/providers/auth-provider";
import { GoogleLoginButton } from "./google-login-button";
import styles from "./auth-page.module.css";

export function GoogleSignupForm() {
  const router = useRouter();
  const { acceptLogin } = useAuth();
  const [pending, setPending] = useState<GooglePending | null>(null);
  const [name, setName] = useState("");
  const [consents, setConsents] = useState({ terms_of_service: false, privacy_collection: false });
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const [expired, setExpired] = useState(false);
  const [retry, setRetry] = useState(0);
  const lock = useRef(false);
  useEffect(() => {
    const controller = new AbortController();
    apiFetch<GooglePending>("/api/v1/auth/google/pending", { signal: controller.signal }).then(value => {
      if (controller.signal.aborted) return;
      setPending(value);
      const initial = value.profile_name?.trim() ?? "";
      setName(initial.length <= 30 ? initial : "");
      setExpired(Date.parse(value.expires_at) <= Date.now());
    }).catch(error => {
      if (controller.signal.aborted) return;
      setNotice(error instanceof ApiRequestError ? error.message : "가입 정보를 확인할 수 없어요.");
      setExpired(error instanceof ApiRequestError && error.code === "OAUTH_PROOF_INVALID");
    });
    return () => controller.abort();
  }, [retry]);
  useEffect(() => {
    if (!pending) return;
    const timeout = window.setTimeout(() => setExpired(true), Math.max(0, Date.parse(pending.expires_at) - Date.now()));
    return () => window.clearTimeout(timeout);
  }, [pending]);
  function returnToStart() {
    const storage = browserRoutingStorage();
    const { origin } = readGoogleContext(storage); clearGoogleContext(storage); router.replace(origin);
  }
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!pending || lock.current || expired) return;
    if (Date.parse(pending.expires_at) <= Date.now()) { setExpired(true); return; }
    lock.current = true; setBusy(true); setNotice("");
    try {
      const member = await apiFetch<Member>("/api/v1/auth/google/signup", {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name, csrf_token: pending.csrf_token,
          consents: Object.entries(legalDocuments).map(([type, value]) => ({ type, version: value.version, agreed: consents[type as keyof typeof consents] })) }),
      });
      acceptLogin(member); clearGoogleContext(browserRoutingStorage()); router.replace("/");
    } catch (error) {
      setNotice(error instanceof ApiRequestError ? error.message : "가입을 완료하지 못했어요. 다시 시도해 주세요.");
      if (error instanceof ApiRequestError && ["OAUTH_PROOF_INVALID", "EMAIL_EXISTS", "OAUTH_LINK_CONFLICT"].includes(error.code)) setExpired(true);
    } finally { lock.current = false; setBusy(false); }
  }
  async function cancel() {
    if (lock.current) return;
    if (!pending) { returnToStart(); return; }
    lock.current = true; setBusy(true);
    try {
      await apiFetch<null>("/api/v1/auth/google/cancel", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ csrf_token: pending.csrf_token }) });
      returnToStart();
    } catch (error) {
      if (error instanceof ApiRequestError && error.code === "OAUTH_PROOF_INVALID") returnToStart();
      else setNotice(error instanceof ApiRequestError ? error.message : "취소하지 못했어요. 다시 시도해 주세요.");
    } finally { lock.current = false; setBusy(false); }
  }
  return <form className={`${styles.card} ${styles.signupCard}`} onSubmit={submit} aria-busy={busy}>
    <h2 className={styles.cardTitle}>Google 회원가입</h2>
    {pending && !expired ? <>
      <div className={styles.fields}>
        <label className={styles.field}><span className={styles.srOnly}>이메일</span><input aria-label="이메일" type="email" value={pending.email} readOnly /></label>
        <label className={styles.field}><span className={styles.srOnly}>이름</span><input aria-label="이름" name="name" placeholder="이름을 입력해주세요." autoComplete="name" maxLength={30} required pattern=".*\S.*" value={name} disabled={busy} onChange={e => setName(e.target.value)} /></label>
      </div>
      {Object.entries(legalDocuments).map(([type, document]) => <div className={styles.consent} key={type}>
        <label><input type="checkbox" required checked={consents[type as keyof typeof consents]} disabled={busy} onChange={e => setConsents(old => ({ ...old, [type]: e.target.checked }))} />{document.title}에 동의합니다. (필수)</label>
        <a href={document.href} target="_blank" rel="noopener noreferrer">전문 보기</a>
      </div>)}
      <button className={styles.primaryButton} disabled={busy || !name.trim() || !consents.terms_of_service || !consents.privacy_collection}>{busy ? "가입 중…" : "가입하기"}</button>
    </> : expired ? <><p className={styles.notice}>Google 인증을 다시 시작해 주세요.</p><GoogleLoginButton origin="/signup" disabled={busy} /></> : <>
      <p role="status">가입 정보를 확인하고 있어요.</p>
      {notice ? <button type="button" className={styles.primaryButton} onClick={() => { setNotice(""); setRetry(v => v + 1); }}>다시 확인</button> : null}
    </>}
    {notice ? <p className={styles.error} role="alert">{notice}</p> : null}
    <button type="button" className={styles.forgot} disabled={busy} onClick={() => void cancel()}>취소하고 돌아가기</button>
  </form>;
}
