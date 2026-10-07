import type { Metadata } from "next";
import Image from "next/image";
import Link from "next/link";
import { PageShell } from "@/components/page-shell";
import { sharedPages } from "@/lib/shared-pages";
import styles from "./guide.module.css";

export const metadata: Metadata = { title: `${sharedPages.guide.title} | 고민일기` };

const steps = [
  { title: "이야기를 들려주세요", description: "편안하게 오늘의 마음을 말해요.", width: 648, height: 404 },
  { title: "마음을 함께 정리해요", description: "천천히 털어놓으며 고민을 정리해요.", width: 620, height: 382 },
  { title: "한 장면으로 남겨요", description: "대화가 끝나면 그림이 완성돼요.", width: 868, height: 632 },
  { title: "컬렉션에 모아봐요", description: "오늘을 차곡차곡 간직해요.", width: 860, height: 604 },
];

export default function Page() {
  return (
    <PageShell page="guide" contentClassName={styles.content}>
      <a className={styles.help} href="#guide-steps" aria-label="고민일기 이용 단계 보기">?</a>
      <section className={styles.intro} aria-labelledby="guide-title">
        <h1 id="guide-title">마음이 가벼워지는 여정</h1>
        <p>고민일기와 이렇게 이야기해요.</p>
        <div className={styles.hero}>
          <Image src="/images/guide/mori-0-4x.png" width={968} height={432} sizes="(min-width: 768px) 23vw, 33vw" alt="" priority />
          <p>언제나,<br className={styles.desktopBreak} /> 네 곁에.</p>
        </div>
      </section>
      <ol id="guide-steps" className={styles.steps} aria-label="고민일기 이용 단계">
        {steps.map((step, index) => (
          <li className={styles.card} key={step.title}>
            <span className={styles.number} aria-hidden="true">{index + 1}</span>
            <div className={styles.illustration}>
              <Image className={index < 2 ? styles.wide : styles.tall} src={`/images/guide/mori-${index + 1}-4x.png`} width={step.width} height={step.height} sizes="(min-width: 768px) 18vw, 28vw" alt="" />
            </div>
            <div className={styles.description}>
              <h2>{step.title}</h2>
              <p>{step.description}</p>
            </div>
          </li>
        ))}
      </ol>
      <Link className={styles.cta} href="/talk">털어놓기 <span aria-hidden="true">→</span></Link>
    </PageShell>
  );
}
