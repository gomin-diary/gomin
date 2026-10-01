import Link from "next/link";
import { PageShell } from "@/components/page-shell";
import { sharedPages, type PageId } from "@/lib/shared-pages";

export function PreparationPage({ page }: { page: PageId }) {
  return (
    <PageShell page={page}>
      <section className="preparation-card" aria-labelledby="page-heading">
        <p className="page-eyebrow">고민일기</p>
        <h1 id="page-heading">{sharedPages[page].title}</h1>
        <p>이 공간을 준비하고 있어요.</p>
        <p>곧 당신의 이야기를 천천히 만나볼게요.</p>
        {page === "home" ? <div className="page-actions"><Link href="/guide">가이드 둘러보기</Link><Link href="/talk">대화 화면으로 이동</Link></div> : <Link className="back-link" href="/">홈으로 돌아가기</Link>}
        {page === "login" ? <Link className="back-link" href="/signup">회원가입 화면으로 이동</Link> : null}
      </section>
    </PageShell>
  );
}
