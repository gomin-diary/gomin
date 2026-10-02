"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { navigationItems } from "@/lib/shared-pages";

export function SiteMenu() {
  const pathname = usePathname();

  return (
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
    </nav>
  );
}
