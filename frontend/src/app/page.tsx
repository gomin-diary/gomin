import Image from "next/image";
import Link from "next/link";
import { AuthGuard } from "@/components/auth-guard";
import { PageShell } from "@/components/page-shell";
import { navigationItems } from "@/lib/shared-pages";
import styles from "./home.module.css";

const homeShortcuts = [
  ...navigationItems.filter((item) => item.href !== "/"),
  { href: "/settings", label: "프로필", icon: "profile" },
];

export default function Home() {
  return (
    <AuthGuard>
      <PageShell page="home" contentClassName={styles.content}>
        <section className={styles.hero} aria-labelledby="home-title">
          <div className={styles.intro}>
            <h1 id="home-title">오늘,<br />어떤 이야기를<br />들려줄래?</h1>
            <p>너의 고민이 모여<br />더 특별한 하루가 돼요.</p>
          </div>
          <nav className={styles.illustratedMenu} aria-label="홈 바로가기">
            {homeShortcuts.map((item) => (
              <Link key={item.href} href={item.href}>
                <span className={styles.shortcutIllustration}>
                  <Image
                    src={item.icon === "profile" ? "/images/navigation/profile-character.png" : `/images/home/${item.icon}.png`}
                    className={item.icon === "profile" ? styles.profileIcon : undefined}
                    width={96}
                    height={item.icon === "profile" ? 96 : 72}
                    alt=""
                  />
                </span>
                <span>{item.label}</span>
              </Link>
            ))}
          </nav>
          <div className={styles.actions}>
            <Link className={styles.cta} href="/talk">
              털어놓기 <Image src="/images/home/arrow.svg" width={24} height={24} alt="" />
            </Link>
            <div className={styles.memo}>
              <Image src="/images/home/memo.png" width={388} height={300} sizes="(min-width: 768px) 15vw, 18vw" alt="언제나, 네 곁에. - 고민일기" />
            </div>
          </div>
        </section>
      </PageShell>
    </AuthGuard>
  );
}
