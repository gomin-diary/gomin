import type { Metadata } from "next";
import { AuthGuard } from "@/components/auth-guard";
import { PageShell } from "@/components/page-shell";
import { SettingsPanel } from "@/components/settings-panel";

export const metadata: Metadata = { title: "설정 | 고민일기" };

export default function Page() {
  return <PageShell page="settings"><AuthGuard><SettingsPanel /></AuthGuard></PageShell>;
}
