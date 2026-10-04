"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { apiFetch, ApiRequestError } from "@/lib/api";
import { browserRoutingStorage, clearGoogleContext, readGoogleContext, type GooglePending } from "@/lib/google-oauth";
import { useAuth, type Member } from "@/providers/auth-provider";
import styles from "./auth-page.module.css";

export function GoogleOAuthResult({ result, errorCode }: { result: string; errorCode?: string }) {
  const router = useRouter();
  const { acceptLogin } = useAuth();
  const [notice, setNotice] = useState("");
  const [attempt, setAttempt] = useState(0);
  const [context] = useState(() => readGoogleContext(browserRoutingStorage()));
  useEffect(() => {
    const controller = new AbortController();
    const storage = browserRoutingStorage();
    async function resolve() {
      try {
        if (result === "login") {
          const member = await apiFetch<Member>("/api/v1/auth/me", { signal: controller.signal });
          if (controller.signal.aborted) return;
          acceptLogin(member); clearGoogleContext(storage); router.replace(context.next);
        } else if (result === "signup") {
          await apiFetch<GooglePending>("/api/v1/auth/google/pending", { signal: controller.signal });
          if (!controller.signal.aborted) router.replace("/auth/google/signup");
        } else {
          clearGoogleContext(storage);
          router.replace(context.origin + (result === "cancelled" ? "" : `?oauth_error=${encodeURIComponent(errorCode ?? "OAUTH_FAILED")}`));
        }
      } catch (error) {
        if (controller.signal.aborted) return;
        if (error instanceof ApiRequestError && (error.status === 401 || error.code === "OAUTH_PROOF_INVALID")) {
          clearGoogleContext(storage); router.replace(`${context.origin}?oauth_error=OAUTH_PROOF_INVALID`);
        } else {
          setNotice(error instanceof ApiRequestError ? error.message : "인증 결과를 확인할 수 없어요. 다시 시도해 주세요.");
        }
      }
    }
    void resolve();
    return () => controller.abort();
  }, [result, errorCode, attempt, router, acceptLogin, context]);
  return <section className={styles.card} aria-busy={!notice}>
    <h2 className={styles.cardTitle}>Google 로그인</h2>
    <p role={notice ? "alert" : "status"}>{notice || "인증 결과를 확인하고 있어요."}</p>
    {notice ? <button className={styles.primaryButton} onClick={() => { setNotice(""); setAttempt(value => value + 1); }}>다시 확인</button> : null}
  </section>;
}
