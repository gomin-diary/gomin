"use client";

import Image from "next/image";
import { useRouter } from "next/navigation";
import { LogoutButton } from "@/components/logout-button";

export function SettingsPanel() {
  const router = useRouter();
  return <section className="settings-panel" aria-labelledby="settings-title">
    <div className="settings-heading">
      <button type="button" aria-label="뒤로" onClick={() => {
        if (window.history.length > 1) router.back();
        else router.push("/");
      }}><Image src="/images/navigation/back.svg" width={24} height={24} alt="" /></button>
      <h1 id="settings-title">설정</h1>
    </div>
    <div className="settings-content">
      <div className="settings-account">
        <Image src="/images/navigation/profile-character.png" width={40} height={40} alt="" />
        <h2>내 계정</h2>
      </div>
      <LogoutButton />
    </div>
  </section>;
}
