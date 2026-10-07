import type { Metadata } from "next";
import Link from "next/link";
import styles from "./docs.module.css";

export const metadata: Metadata = {
  title: { default: "프로젝트 문서 | 고민일기", template: "%s | 고민일기 문서" },
  description: "고민일기 프로젝트의 설치, 개발, 기능 및 배포 문서",
  robots: { index: false, follow: false },
};

export default function DocsLayout({ children }: { children: React.ReactNode }) {
  return <div className={styles.shell}>
    <a className={styles.skip} href="#docs-content">본문으로 건너뛰기</a>
    <header className={styles.header}>
      <Link className={styles.brand} href="/docs"><span aria-hidden="true">◈</span> 고민일기 <strong>문서</strong></Link>
      <Link className={styles.serviceLink} href="/guide">서비스 가이드 <span aria-hidden="true">↗</span></Link>
    </header>
    {children}
  </div>;
}
