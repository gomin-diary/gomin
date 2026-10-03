"use client";

import { useEffect } from "react";
import { useUiStore } from "@/providers/ui-store-provider";
import styles from "./toast.module.css";

export function Toast() {
  const toast = useUiStore((state) => state.toast);
  const dismissToast = useUiStore((state) => state.dismissToast);
  useEffect(() => {
    if (!toast || toast.action) return;
    const timer = window.setTimeout(() => dismissToast(toast.id), 5000);
    return () => window.clearTimeout(timer);
  }, [toast, dismissToast]);

  return <div className={styles.region} role="status" aria-live="polite" aria-atomic="true">
    {toast ? <div className={styles.toast}>
      <span>{toast.message}</span>
      {toast.action ? <button type="button" onClick={toast.action.onClick}>{toast.action.label}</button> : null}
      <button className={styles.close} type="button" aria-label="알림 닫기" onClick={() => dismissToast(toast.id)}>×</button>
    </div> : null}
  </div>;
}
