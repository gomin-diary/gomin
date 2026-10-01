import Image from "next/image";
import Link from "next/link";
import type { CSSProperties, ReactNode } from "react";
import { SiteMenu } from "@/components/site-menu";
import { sharedPages, type PageId } from "@/lib/shared-pages";

export function PageShell({ page, children }: { page: PageId; children: ReactNode }) {
  const config = sharedPages[page];
  const style = { "--page-mobile-color": config.mobileColor ?? "#faf7f2" } as CSSProperties;
  return (
    <div className={`page-shell page-shell--${page} page-shell--nav-${config.navigation}`} style={style}>
      <a className="skip-link" href="#main-content">본문으로 건너뛰기</a>
      <div className="page-background" aria-hidden="true">
        <picture>
          <source media="(min-width: 768px)" type="image/avif" srcSet={`/images/backgrounds/${config.desktop.asset}.avif`} />
          <source media="(min-width: 768px)" type="image/webp" srcSet={`/images/backgrounds/${config.desktop.asset}.webp`} />
          {config.mobile ? <source type="image/avif" srcSet={`/images/backgrounds/${config.mobile.asset}.avif`} /> : null}
          {/* Native picture keeps viewport-specific sources and AVIF/WebP fallback together. */}
          <img src={`/images/backgrounds/${(config.mobile ?? config.desktop).asset}.webp`} width={config.desktop.width} height={config.desktop.height} alt="" fetchPriority="high" decoding="async" />
        </picture>
      </div>
      <header className="site-header">
        <Link className="site-brand" href="/" aria-label="고민일기 홈">
          <span>고민일기</span>
          <Image src="/images/icons/leaf.svg" width={24} height={24} alt="" />
        </Link>
        {config.navigation !== "none" ? <SiteMenu /> : null}
      </header>
      <main id="main-content" className="page-content" tabIndex={-1}>{children}</main>
    </div>
  );
}
