import type { Metadata } from "next";
import { SummaryDiary } from "@/components/summary-diary";
import { TalkScreen } from "@/components/talk-screen";
import { AuthGuard } from "@/components/auth-guard";
import { sharedPages } from "@/lib/shared-pages";

export const metadata: Metadata = { title: `${sharedPages.talk.title} | 고민일기` };

export default async function Page({ searchParams }: { searchParams: Promise<{ summary?: string }> }) {
  const { summary } = await searchParams;
  return <AuthGuard>{summary ? <SummaryDiary summaryId={summary} /> : <TalkScreen />}</AuthGuard>;
}
