import type { Metadata } from "next";
import { PreparationPage } from "@/components/preparation-page";
import { sharedPages } from "@/lib/shared-pages";

export const metadata: Metadata = { title: `${sharedPages.guide.title} | 고민일기` };

export default function Page() {
  return <PreparationPage page="guide" />;
}
