"use client";

import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useRef, useState, type FormEvent, type InputHTMLAttributes, type ReactNode } from "react";
import { apiFetch, ApiRequestError } from "@/lib/api";
import { useAuth, type Member } from "@/providers/auth-provider";
import { GoogleLoginButton } from "./google-login-button";
import { safeLoginDestination } from "@/lib/google-oauth";
import styles from "./auth-page.module.css";

type FieldProps = InputHTMLAttributes<HTMLInputElement> & {
  label: string;
  icon: "user" | "mail" | "shield" | "lock";
  action?: ReactNode;
};

function AuthField({ label, icon, action, type, ...props }: FieldProps) {
  const [visible, setVisible] = useState(false);
  const password = type === "password";
  return (
    <label className={styles.field}>
      <span className={styles.srOnly}>{label}</span>
      <Image className={styles.fieldIcon} src={`/images/auth/${icon}.svg`} width={24} height={24} alt="" />
      <input aria-label={label} type={password && visible ? "text" : type} {...props} />
      {password ? (
        <button className={styles.visibility} type="button" aria-label={`${label} ${visible ? "숨기기" : "표시"}`} aria-pressed={visible} onClick={() => setVisible(!visible)}>
          <Image src="/images/auth/eye.svg" width={24} height={24} alt="" />
        </button>
      ) : action}
    </label>
  );
}

export function AuthForm({ mode, initialNotice = "" }: { mode: "login" | "signup"; initialNotice?: string }) {
  const signup = mode === "signup";
  const formRef = useRef<HTMLFormElement>(null);
  const [notice, setNotice] = useState(initialNotice);
  const [verificationVisible, setVerificationVisible] = useState(false);
  const [confirmationError, setConfirmationError] = useState(false);
  const [agreed, setAgreed] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const pending = useRef(false);
  const router = useRouter();
  const { acceptLogin } = useAuth();

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (pending.current) return;
    const data = new FormData(event.currentTarget);
    if (signup && data.get("password") !== data.get("confirmation")) {
      setConfirmationError(true);
      formRef.current?.querySelector<HTMLInputElement>("[name=confirmation]")?.focus();
      return;
    }
    setConfirmationError(false);
    if (signup) {
      setNotice("회원가입 기능을 준비하고 있어요. 입력한 정보는 전송하거나 저장하지 않았어요.");
      return;
    }
    pending.current = true;
    setSubmitting(true);
    setNotice("");
    try {
      const member = await apiFetch<Member>("/api/v1/auth/login", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: data.get("email"), password: data.get("password") }),
      });
      acceptLogin(member);
      formRef.current?.reset();
      const destination = new URLSearchParams(window.location.search).get("next");
      router.replace(safeLoginDestination(destination));
    } catch (error) {
      setNotice(error instanceof ApiRequestError ? error.message : "로그인에 실패했어요. 다시 시도해 주세요.");
      formRef.current?.querySelector<HTMLInputElement>("[name=password]")?.focus();
    } finally {
      pending.current = false;
      setSubmitting(false);
    }
  }

  function requestVerification() {
    const email = formRef.current?.querySelector<HTMLInputElement>("[name=email]");
    if (!email?.reportValidity()) return;
    setVerificationVisible(true);
    setNotice("이메일 인증 기능을 준비하고 있어요. 인증 메일은 아직 발송되지 않았어요.");
  }

  return (
    <form ref={formRef} className={`${styles.card} ${signup ? styles.signupCard : styles.loginCard}`} onSubmit={submit} aria-busy={submitting}>
      {signup ? <h2 className={styles.cardTitle}>회원가입</h2> : <h2 className={styles.srOnly}>로그인</h2>}
      <div className={styles.fields}>
        {signup ? <AuthField label="이름" icon="user" name="name" placeholder="이름을 입력해주세요." autoComplete="name" maxLength={50} required pattern=".*\S.*" /> : null}
        <AuthField label="이메일" icon="mail" name="email" type="email" placeholder="이메일을 입력해주세요." autoComplete="email" required onChange={() => { setVerificationVisible(false); setNotice(""); }} action={signup ? <button className={styles.outlineButton} type="button" aria-controls="verification-field" aria-expanded={verificationVisible} onClick={requestVerification}>인증 요청</button> : undefined} />
        {signup && verificationVisible ? (
          <div id="verification-field">
            <AuthField label="인증번호" icon="shield" name="verification" placeholder="인증번호 6자리" inputMode="numeric" autoComplete="one-time-code" maxLength={6} pattern="[0-9]{6}" action={<button className={styles.outlineButton} type="button" onClick={() => setNotice("이메일 인증 기능을 준비하고 있어요. 지금은 인증번호를 확인할 수 없어요.")}>확인</button>} />
          </div>
        ) : null}
        <AuthField label="비밀번호" icon="lock" name="password" type="password" placeholder="비밀번호를 입력해주세요." autoComplete={signup ? "new-password" : "current-password"} minLength={signup ? 8 : undefined} required onChange={() => { setConfirmationError(false); setNotice(""); }} />
        {signup ? <AuthField label="비밀번호 확인" icon="lock" name="confirmation" type="password" placeholder="비밀번호를 다시 입력해주세요." autoComplete="new-password" minLength={8} required aria-invalid={confirmationError} aria-describedby={confirmationError ? "confirmation-error" : undefined} onChange={() => setConfirmationError(false)} /> : null}
      </div>
      {confirmationError ? <p id="confirmation-error" className={styles.error} role="alert">비밀번호가 일치하지 않아요. 다시 확인해주세요.</p> : null}
      {signup ? (
        <label className={styles.consent}>
          <input name="consent" type="checkbox" required checked={agreed} onChange={(event) => setAgreed(event.target.checked)} />
          <span>이용약관 및 개인정보 처리방침에 동의합니다.</span>
        </label>
      ) : <button className={styles.forgot} type="button" onClick={() => setNotice("비밀번호 찾기 기능을 준비하고 있어요.")}>비밀번호를 잊으셨나요?</button>}
      <button className={styles.primaryButton} type="submit" disabled={submitting || (signup && !agreed)}>{signup ? "가입하기" : submitting ? "로그인 중…" : "로그인"}</button>
      {signup ? <div className={styles.rule} /> : (
        <>
          <div className={styles.divider}><span>또는</span></div>
          <GoogleLoginButton origin="/login" disabled={submitting} />
        </>
      )}
      <div className={styles.switchAccount}>
        <span>{signup ? "이미 계정이 있으신가요?" : "아직 계정이 없으신가요?"}</span>
        <Link href={signup ? "/login" : "/signup"}>{signup ? "로그인" : "회원가입"}<span aria-hidden="true"> ›</span></Link>
      </div>
      <div role="status" aria-live="polite" aria-atomic="true" className={notice ? styles.notice : styles.srOnly}>{notice}</div>
    </form>
  );
}
