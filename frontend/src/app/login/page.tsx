import type { Metadata } from "next";
import { AuthPage } from "@/components/auth-page";
import { sharedPages } from "@/lib/shared-pages";

export const metadata: Metadata = { title: `${sharedPages.login.title} | 고민일기` };

export default async function Page({ searchParams }: { searchParams: Promise<{ reason?: string }> }) {
  const { reason } = await searchParams;
  return <AuthPage mode="login" initialNotice={reason === "auth" ? "로그인이 필요하거나 세션이 만료되었어요. 다시 로그인해 주세요." : undefined} />;
}
