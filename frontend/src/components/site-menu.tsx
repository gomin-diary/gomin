"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { navigationItems } from "@/lib/shared-pages";
import { DesktopAccount } from "@/components/desktop-account";
import { useAuth } from "@/providers/auth-provider";

export function SiteMenu() {
  const pathname = usePathname();
  const { member, error, refresh } = useAuth();
  const profileActive = pathname === "/settings" || pathname.startsWith("/settings/");
  const profile = <><Image className="site-menu__icon" src={`/images/navigation/profile${profileActive ? "-active" : ""}.svg`} width={32} height={32} alt="" /><span>프로필</span></>;

  return (
    <div className="site-header__actions">
    <nav className="site-menu" aria-label="주 메뉴">
      {navigationItems.map(({ href, label, icon }) => {
        const active = href === "/" ? pathname === href : pathname === href || pathname.startsWith(`${href}/`);
        return (
          <Link key={href} href={href} className="site-menu__link" aria-current={active ? "page" : undefined}>
            <Image className="site-menu__icon" src={`/images/navigation/${icon}${active ? "-active" : ""}.svg`} width={32} height={32} alt="" />
            <span>{label}</span>
          </Link>
        );
      })}
      {member === undefined ? <button className="site-menu__link site-menu__profile" type="button" disabled={!error} aria-label={error ? "로그인 상태 다시 확인" : "로그인 상태 확인 중"} onClick={() => void refresh()}>{profile}</button> : <Link className="site-menu__link site-menu__profile" href={member ? "/settings" : "/login"} aria-current={profileActive ? "page" : undefined}>{profile}</Link>}
    </nav>
    <DesktopAccount key={pathname} />
    </div>
  );
}
