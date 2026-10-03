import Link from "next/link";
import { legalDocuments } from "@/content/legal";

export function LegalDocument({ type }: { type: keyof typeof legalDocuments }) {
  const document = legalDocuments[type];
  return <main style={{ maxWidth: 760, margin: "40px auto", padding: 24, lineHeight: 1.8 }}>
    <h1>{document.title}</h1><p>개발용 초안 · 버전 {document.version}</p>
    {document.paragraphs.map((paragraph) => <p key={paragraph}>{paragraph}</p>)}
    <Link href="/signup">회원가입으로 돌아가기</Link>
  </main>;
}
