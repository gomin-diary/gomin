import type { Metadata } from "next";
import { PreparationPage } from "@/components/preparation-page";
import { AuthGuard } from "@/components/auth-guard";
import { sharedPages } from "@/lib/shared-pages";

export const metadata: Metadata = { title: `${sharedPages.talk.title} | 고민일기` };

export default function Page() {
  return <AuthGuard><PreparationPage page="talk" /></AuthGuard>;
}
