"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect, useRef } from "react";
import { LogoutButton } from "@/components/logout-button";
import { useAuth } from "@/providers/auth-provider";

export function DesktopAccount() {
  const { member } = useAuth();
  const details = useRef<HTMLDetailsElement>(null);
  const trigger = useRef<HTMLElement>(null);

  useEffect(() => {
    function close(event: PointerEvent) {
      if (event.target instanceof Node && !details.current?.contains(event.target) && details.current) details.current.open = false;
    }
    document.addEventListener("pointerdown", close);
    return () => document.removeEventListener("pointerdown", close);
  }, []);

  if (!member) return null;

  const avatar = <Image src="/images/navigation/profile-character.png" width={78} height={78} alt="" />;

  return <details className="desktop-account" ref={details} onKeyDown={(event) => {
    if (event.key === "Escape" && details.current?.open) {
      details.current.open = false;
      trigger.current?.focus();
    }
  }}>
    <summary className="account-avatar" ref={trigger} aria-label="프로필 메뉴">{avatar}</summary>
    <div className="account-dropdown">
      <Link className="account-action" href="/settings">
        <Image src="/images/navigation/settings.svg" width={20} height={20} alt="" />
        <span>내 계정</span>
        <Image className="account-action__next" src="/images/navigation/next.svg" width={20} height={20} alt="" />
      </Link>
      <div className="account-divider" />
      <LogoutButton />
    </div>
  </details>;
}
