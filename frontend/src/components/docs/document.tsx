import Link from "next/link";
import { MarkdownContent } from "@/lib/docs-renderer.mjs";
import { documents, navigation, type Document } from "@/lib/docs";
import { MermaidDiagram } from "./mermaid";
import { DocOutline } from "./outline";
import styles from "@/app/docs/docs.module.css";

export function DocDocument({ document }: { document: Document }) {
  const headings = document.headings.filter(heading => heading.depth === 2 || heading.depth === 3);
  return <div className={styles.workspace}>
    <aside className={styles.sidebar} aria-label="문서 메뉴">
      <DocOutline title="문서 목록">
        <nav>
          <Link href="/docs" aria-current={document.slug === "" ? "page" : undefined} className={styles.homeLink}>문서 홈</Link>
          {navigation.map(group => <details key={group.title} className={styles.navGroup} open={group.items.some(item => item.url === document.url)}>
            <summary><h2>{group.title}</h2></summary>
            <ul>{group.items.map(item => <li key={item.url}>
              <Link href={item.url} aria-current={item.url === document.url ? "page" : undefined}>{item.title}</Link>
            </li>)}</ul>
          </details>)}
        </nav>
      </DocOutline>
    </aside>
    <main id="docs-content" className={styles.article} tabIndex={-1}>
      <div className={styles.breadcrumb}><Link href="/docs">문서</Link>{document.slug ? <><span aria-hidden="true">/</span><span>{document.title}</span></> : null}</div>
      <div className={styles.markdown}>
        <MarkdownContent markdown={document.markdown} source={document.source} documents={documents} Diagram={MermaidDiagram} />
      </div>
    </main>
    {headings.length ? <aside className={styles.toc} aria-label="본문 목차">
      <DocOutline title="이 문서에서">
        <nav><ul>{headings.map(heading => <li key={heading.id} data-depth={heading.depth}>
          <a href={`#${heading.id}`}>{heading.text}</a>
        </li>)}</ul></nav>
      </DocOutline>
    </aside> : null}
  </div>;
}
