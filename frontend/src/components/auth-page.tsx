import Image from "next/image";
import Link from "next/link";
import { AuthForm } from "@/components/auth-form";
import { PageShell } from "@/components/page-shell";
import styles from "./auth-page.module.css";

export function AuthPage({ mode }: { mode: "login" | "signup" }) {
  const signup = mode === "signup";
  return (
    <PageShell page={mode} contentClassName={styles.content}>
      <section className={`${styles.authPage} ${signup ? styles.signup : styles.login}`} aria-labelledby="auth-heading">
        <div className={styles.hero}>
          <p className={styles.eyebrow}>GOMINILGI</p>
          <Link href="/" className={styles.heroBrand} aria-label="고민일기 홈"><span>고민일기</span><Image src="/images/icons/leaf.svg" width={24} height={24} alt="" /></Link>
          <h1 id="auth-heading" className={styles.heading}>
            {signup ? <>처음 만나는 마음,<Image src="/images/icons/leaf.svg" width={32} height={32} alt="" /></> : <><span className={styles.desktopHeading}>오늘도,<br />조금 더 가벼운 마음으로.</span><span className={styles.mobileHeading}>오늘도, 좋은 하루가 되기를.</span></>}
          </h1>
          <p className={styles.supporting}>{signup ? "당신의 이야기를 천천히 시작해보세요." : <>당신의 이야기가<span className={styles.mobileBreak}><br /></span><span className={styles.desktopSpace}> </span>오늘을 조금 더 편안하게 만들어요.</>}</p>
        </div>
        <AuthForm mode={mode} />
        <p className={`${styles.sideCopy} ${styles.sideLeft}`} aria-hidden="true">기록하는 순간,<br />마음이 가벼워져요.</p>
        <p className={`${styles.sideCopy} ${styles.sideRight}`} aria-hidden="true">언제나,<br />네 곁에.</p>
      </section>
    </PageShell>
  );
}
