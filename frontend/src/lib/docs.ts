import manifest from "@/generated/docs.json";
import type { Heading } from "./docs-markdown.mjs";

export type Document = { source: string; slug: string; url: string; title: string; markdown: string; headings: Heading[] };
export const documents: Document[] = manifest.documents;
export const navigation = manifest.navigation;
export function getDocument(slug: string): Document | undefined {
  return documents.find(document => document.slug === slug);
}
