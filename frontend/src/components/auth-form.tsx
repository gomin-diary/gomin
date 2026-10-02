"use client";

import Image from "next/image";
import Link from "next/link";
import { useRef, useState, type FormEvent, type InputHTMLAttributes, type ReactNode } from "react";
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

export function AuthForm({ mode }: { mode: "login" | "signup" }) {
  const signup = mode === "signup";
  const formRef = useRef<HTMLFormElement>(null);
  const [notice, setNotice] = useState("");
  const [verificationVisible, setVerificationVisible] = useState(false);
  const [confirmationError, setConfirmationError] = useState(false);
  const [agreed, setAgreed] = useState(false);

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    if (signup && data.get("password") !== data.get("confirmation")) {
      setConfirmationError(true);
      formRef.current?.querySelector<HTMLInputElement>("[name=confirmation]")?.focus();
      return;
    }
    setConfirmationError(false);
    setNotice(signup ? "회원가입 기능을 준비하고 있어요. 입력한 정보는 전송하거나 저장하지 않았어요." : "로그인 기능을 준비하고 있어요. 입력한 정보는 전송하거나 저장하지 않았어요.");
  }

  function requestVerification() {
    const email = formRef.current?.querySelector<HTMLInputElement>("[name=email]");
    if (!email?.reportValidity()) return;
    setVerificationVisible(true);
    setNotice("이메일 인증 기능을 준비하고 있어요. 인증 메일은 아직 발송되지 않았어요.");
  }

  return (
    <form ref={formRef} className={`${styles.card} ${signup ? styles.signupCard : styles.loginCard}`} onSubmit={submit}>
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
      <button className={styles.primaryButton} type="submit" disabled={signup && !agreed}>{signup ? "가입하기" : "로그인"}</button>
      {signup ? <div className={styles.rule} /> : (
        <>
          <div className={styles.divider}><span>또는</span></div>
          <div className={styles.socialButtons}>
            {([['apple', 'Apple'], ['google', 'Google'], ['naver', '네이버']] as const).map(([icon, name]) => (
              <button key={icon} type="button" aria-label={`${name}로 로그인`} onClick={() => setNotice(`${name} 로그인 기능을 준비하고 있어요.`)}>
                <Image src={`/images/auth/${icon}.svg`} width={40} height={40} alt="" />
              </button>
            ))}
          </div>
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
