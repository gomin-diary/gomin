import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { DocDocument } from "@/components/docs/document";
import { documents, getDocument } from "@/lib/docs";

export const dynamicParams = false;
export function generateStaticParams() {
  return documents.filter(document => document.slug).map(document => ({ slug: document.slug.split("/") }));
}
type Props = { params: Promise<{ slug: string[] }> };
export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const document = getDocument((await params).slug.join("/"));
  if (!document) notFound();
  return { title: document.title };
}
export default async function DocumentPage({ params }: Props) {
  const document = getDocument((await params).slug.join("/"));
  if (!document) notFound();
  return <DocDocument document={document} />;
}
