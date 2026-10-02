"use client";

import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState, type FormEvent, type InputHTMLAttributes, type ReactNode } from "react";
import { apiFetch, ApiRequestError } from "@/lib/api";
import { legalDocuments } from "@/content/legal";
import styles from "./auth-page.module.css";

type FieldProps = InputHTMLAttributes<HTMLInputElement> & { label: string; icon: string; action?: ReactNode };
function Field({ label, icon, action, type, ...props }: FieldProps) {
  const [visible, setVisible] = useState(false);
  const password = type === "password";
  return <label className={styles.field}>
    <span className={styles.srOnly}>{label}</span>
    <Image className={styles.fieldIcon} src={`/images/auth/${icon}.svg`} width={24} height={24} alt="" />
    <input aria-label={label} type={password && visible ? "text" : type} {...props} />
    {password ? <button className={styles.visibility} type="button" aria-label={`${label} ${visible ? "숨기기" : "표시"}`} aria-pressed={visible} onClick={() => setVisible(!visible)}>
      <Image src="/images/auth/eye.svg" width={24} height={24} alt="" />
    </button> : action}
  </label>;
}

type Verification = { verification_id: string; expires_at: string };
type Proof = { verification_proof: string; expires_at: string };

export function SignupForm() {
  const router = useRouter();
  const form = useRef<HTMLFormElement>(null);
  const lock = useRef(false);
  const [busy, setBusy] = useState("");
  const [notice, setNotice] = useState("");
  const [failed, setFailed] = useState(false);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [code, setCode] = useState("");
  const [verification, setVerification] = useState<Verification | null>(null);
  const [proof, setProof] = useState<Proof | null>(null);
  const [consents, setConsents] = useState({ terms_of_service: false, privacy_collection: false });
  const [now, setNow] = useState(0);
  const [confirmationError, setConfirmationError] = useState(false);
  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, []);
  const expiresAt = proof?.expires_at ?? verification?.expires_at;
  const remaining = expiresAt ? Math.max(0, Math.ceil((Date.parse(expiresAt) - now) / 1000)) : 0;
  const expired = !!expiresAt && now > 0 && remaining === 0;
  const canSubmit = name.trim().length > 0 && name.trim().length <= 30 && !!proof && !expired &&
    password.length >= 8 && password === confirmation && consents.terms_of_service && consents.privacy_collection;

  function resetVerification() { setProof(null); setVerification(null); setCode(""); setNotice(""); setFailed(false); }
  function showError(error: unknown) {
    setFailed(true);
    setNotice(error instanceof ApiRequestError ? error.message : "요청을 처리하지 못했어요. 잠시 후 다시 시도해 주세요.");
    if (error instanceof ApiRequestError && ["PROOF_INVALID", "CODE_EXPIRED", "VERIFICATION_INVALID"].includes(error.code)) setProof(null);
  }
  async function request<T>(action: string, body: unknown): Promise<T> {
    return apiFetch<T>(`/api/v1/auth/${action}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  }
  async function sendCode() {
    if (lock.current || !form.current?.querySelector<HTMLInputElement>("[name=email]")?.reportValidity()) return;
    lock.current = true; setBusy("send"); resetVerification();
    try {
      const result = await request<Verification>("email-verifications", { email });
      setVerification(result); setNow(Date.now()); setNotice("인증 메일을 요청했어요. 수신한 6자리 번호를 3분 안에 입력해 주세요.");
    } catch (error) { showError(error); }
    finally { lock.current = false; setBusy(""); }
  }
  async function confirmCode() {
    if (lock.current || !verification || !form.current?.querySelector<HTMLInputElement>("[name=verification]")?.reportValidity()) return;
    lock.current = true; setBusy("confirm"); setFailed(false);
    try {
      const result = await request<Proof>("email-verifications/confirm", { email, verification_id: verification.verification_id, code });
      setProof(result); setCode(""); setNow(Date.now()); setNotice("이메일 인증이 완료됐어요. 30분 안에 가입을 완료해 주세요.");
    } catch (error) { showError(error); }
    finally { lock.current = false; setBusy(""); }
  }
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (lock.current) return;
    if (password !== confirmation) { setConfirmationError(true); form.current?.querySelector<HTMLInputElement>("[name=confirmation]")?.focus(); return; }
    if (!canSubmit || (proof && Date.parse(proof.expires_at) <= Date.now())) {
      setFailed(true); setNotice("이메일 인증과 필수 약관 동의를 확인해 주세요."); return;
    }
    lock.current = true; setBusy("signup"); setFailed(false);
    try {
      await request("signup", { name, email, password, confirmation, verification_proof: proof!.verification_proof,
        consents: Object.entries(legalDocuments).map(([type, document]) => ({ type, version: document.version, agreed: true })) });
      setPassword(""); setConfirmation(""); setProof(null);
      router.replace("/"); router.refresh();
    } catch (error) { showError(error); }
    finally { lock.current = false; setBusy(""); }
  }
  return <form ref={form} className={`${styles.card} ${styles.signupCard}`} onSubmit={submit} aria-busy={!!busy}>
    <h2 className={styles.cardTitle}>회원가입</h2>
    <div className={styles.fields}>
      <Field label="이름" icon="user" name="name" placeholder="이름을 입력해주세요." autoComplete="name" maxLength={30} required pattern=".*\S.*" value={name} disabled={!!busy} onChange={(event) => setName(event.target.value)} />
      <Field label="이메일" icon="mail" name="email" type="email" placeholder="이메일을 입력해주세요." autoComplete="email" required value={email} disabled={!!busy} readOnly={!!proof}
        onChange={(event) => { setEmail(event.target.value); resetVerification(); }} action={<button className={styles.outlineButton} type="button" disabled={!!busy} onClick={proof ? resetVerification : sendCode}>{proof ? "이메일 변경" : busy === "send" ? "발송 중" : verification ? "재발송" : "인증 요청"}</button>} />
      {verification && !proof ? <div>
        <Field label="인증번호" icon="shield" name="verification" placeholder="인증번호 6자리" inputMode="numeric" autoComplete="one-time-code" maxLength={6} pattern="[0-9]{6}" required value={code} disabled={!!busy}
          onChange={(event) => setCode(event.target.value)} action={<button className={styles.outlineButton} type="button" disabled={!!busy || expired} onClick={confirmCode}>{busy === "confirm" ? "확인 중" : "확인"}</button>} />
      </div> : null}
      <Field label="비밀번호" icon="lock" name="password" type="password" placeholder="비밀번호를 입력해주세요." autoComplete="new-password" minLength={8} maxLength={1024} required value={password} disabled={!!busy} onChange={(event) => { setPassword(event.target.value); setConfirmationError(false); }} />
      <Field label="비밀번호 확인" icon="lock" name="confirmation" type="password" placeholder="비밀번호를 다시 입력해주세요." autoComplete="new-password" minLength={8} maxLength={1024} required value={confirmation} disabled={!!busy} aria-invalid={confirmationError} aria-describedby={confirmationError ? "confirmation-error" : undefined}
        onBlur={() => setConfirmationError(confirmation.length > 0 && password !== confirmation)} onChange={(event) => { setConfirmation(event.target.value); setConfirmationError(false); }} />
    </div>
    {expiresAt ? <p className={styles.notice}>{expired ? "인증 시간이 만료됐어요. 이메일 인증을 다시 시작해 주세요." : `${proof ? "가입 완료까지" : "인증번호 유효시간"} ${Math.floor(remaining / 60)}:${String(remaining % 60).padStart(2, "0")}`}</p> : null}
    {proof && expired ? <button type="button" className={styles.outlineButton} onClick={resetVerification}>다시 인증하기</button> : null}
    {confirmationError ? <p id="confirmation-error" className={styles.error} role="alert">비밀번호가 일치하지 않아요. 다시 확인해주세요.</p> : null}
    {Object.entries(legalDocuments).map(([type, document]) => <div key={type} className={styles.consent}>
      <label><input type="checkbox" required disabled={!!busy} checked={consents[type as keyof typeof consents]} onChange={(event) => setConsents({ ...consents, [type]: event.target.checked })} /> {document.title}에 동의합니다. (필수)</label>
      <Link href={document.href} target="_blank" rel="noopener noreferrer" aria-label={`${document.title} 전문 보기 (새 창)`}>전문 보기</Link>
    </div>)}
    <p className={styles.draftNote}>약관은 개발용 초안입니다.</p>
    <button className={styles.primaryButton} type="submit" disabled={!!busy || !canSubmit}>{busy === "signup" ? "가입 중…" : "가입하기"}</button>
    <div className={styles.rule} />
    <div className={styles.switchAccount}><span>이미 계정이 있으신가요?</span><Link href="/login">로그인<span aria-hidden="true"> ›</span></Link></div>
    <div role={failed ? "alert" : "status"} aria-live="polite" className={notice ? failed ? styles.error : styles.notice : styles.srOnly}>{notice}</div>
  </form>;
}
