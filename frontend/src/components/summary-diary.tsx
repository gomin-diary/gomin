"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { PageShell } from "@/components/page-shell";
import { useAuth } from "@/providers/auth-provider";
import { apiFetch } from "@/lib/api";
import { formatEncouragement } from "@/lib/diary-text";
import styles from "./summary-diary.module.css";

type Summary = { id: string; current_feeling: string; main_concerns: string[]; emotion_tags: string[] };
type Result = { id: string; title: string; encouragement_text: string; diary_date: string; image_url: string };

export function SummaryDiary({ summaryId }: { summaryId: string }) {
  const { member } = useAuth();
  return member ? <MemberDiary key={`${member.id}:${summaryId}`} summaryId={summaryId} /> : null;
}

function MemberDiary({ summaryId }: { summaryId: string }) {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [result, setResult] = useState<Result | null>(null);
  const [pending, setPending] = useState(false);
  const [entryId, setEntryId] = useState<string | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    const controller = new AbortController();
    void apiFetch<Summary>(`/api/v1/summaries/${encodeURIComponent(summaryId)}`, { signal: controller.signal })
      .then(setSummary).catch(() => { if (!controller.signal.aborted) setError("요약을 불러올 수 없어요."); });
    return () => controller.abort();
  }, [summaryId]);
  async function generate() {
    if (pending) return;
    setPending(true); setError("");
    try {
      setResult(await apiFetch<Result>("/api/v1/diary-images", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ summary_id: summaryId }),
      }));
    } catch { setError("이미지를 만들지 못했어요. 다시 시도해 주세요."); }
    finally { setPending(false); }
  }
  async function save() {
    if (!result || pending) return;
    setPending(true); setError("");
    try {
      const entry = await apiFetch<{ id: string }>(`/api/v1/diary-results/${result.id}/collection-entry`, { method: "POST" });
      setEntryId(entry.id);
    } catch { setError("컬렉션에 저장하지 못했어요. 다시 시도해 주세요."); }
    finally { setPending(false); }
  }
  return <PageShell page="talk"><section className={styles.card}>
    {result ? <>
      <h1>{result.title}</h1><time dateTime={result.diary_date}>{result.diary_date}</time>
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img className={styles.image} src={result.image_url} alt="요약을 바탕으로 생성한 그림일기" />
      <p className={styles.encouragement}>{formatEncouragement(result.encouragement_text)}</p>
      {entryId ? <p role="status">컬렉션에 저장했어요. <Link href={`/collection#entry=${entryId}`}>저장한 일기 보기</Link></p>
        : <button type="button" disabled={pending} onClick={() => void save()}>{pending ? "저장하는 중이에요…" : "컬렉션에 저장하기"}</button>}
    </> : <>
      <h1>오늘의 마음을 그림으로 남겨요</h1>
      {summary ? <><p>{summary.current_feeling}</p><ul>{summary.main_concerns.map((text, i) => <li key={i}>{text}</li>)}</ul>
        <p>{summary.emotion_tags.join(" · ")}</p>
        <button type="button" disabled={pending} onClick={() => void generate()}>{pending ? "그림을 만들고 있어요…" : "이 요약으로 그림 만들기"}</button>
      </> : !error && <p role="status">요약을 불러오는 중이에요.</p>}
    </>}
    {error && <p role="alert">{error}</p>}
  </section></PageShell>;
}
