import Link from "next/link";
import styles from "./docs.module.css";

export default function DocumentNotFound() {
  return <main id="docs-content" className={styles.missing}>
    <h1>문서를 찾을 수 없습니다</h1>
    <p>문서 목록에서 원하는 문서를 선택해 주세요.</p>
    <Link href="/docs">문서 목록으로</Link>
  </main>;
}
