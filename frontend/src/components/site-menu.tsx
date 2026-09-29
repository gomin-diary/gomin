"use client";

import { useUiStore } from "@/providers/ui-store-provider";

export function SiteMenu() {
  const isOpen = useUiStore((state) => state.isMenuOpen);
  const toggleMenu = useUiStore((state) => state.toggleMenu);

  return (
    <div>
      <button type="button" aria-expanded={isOpen} aria-controls="site-menu" onClick={toggleMenu}>
        {isOpen ? "메뉴 닫기" : "메뉴 열기"}
      </button>
      <nav id="site-menu" hidden={!isOpen} aria-label="주 메뉴">
        <a href="/">홈</a>
      </nav>
    </div>
  );
}
