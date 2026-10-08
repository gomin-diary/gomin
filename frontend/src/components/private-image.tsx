"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";

/** Component-scoped URLs are discarded on account change/unmount. Never cache signed URLs globally. */
export function PrivateImage({ accessPath, alt = "", className, retryable = false }: { accessPath: string; alt?: string; className?: string; retryable?: boolean }) {
  const [retry, setRetry] = useState(0);
  const [state, setState] = useState<{ path: string; url: string; error: boolean } | null>(null);
  useEffect(() => {
    const abort = new AbortController();
    let timer: ReturnType<typeof setTimeout>;
    const load = async () => {
      try {
        const image = await apiFetch<{ url: string; expires_at: string }>(accessPath, { signal: abort.signal });
        if (abort.signal.aborted) return;
        if (!image.url || !Number.isFinite(Date.parse(image.expires_at)) || Date.parse(image.expires_at) <= Date.now() + 1000) throw new Error("Invalid image response");
        setState({ path: accessPath, url: image.url, error: false });
        timer = setTimeout(() => { void load(); }, Math.max(1000, Date.parse(image.expires_at) - Date.now() - 10000));
      } catch {
        if (!abort.signal.aborted) setState({ path: accessPath, url: "", error: true });
      }
    };
    void load();
    return () => { abort.abort(); clearTimeout(timer); };
  }, [accessPath, retry]);
  const current = state?.path === accessPath ? state : null;
  if (current?.error) return <span role="alert">이미지를 불러오지 못했어요. {retryable && <button type="button" onClick={() => setRetry(value => value + 1)}>다시 불러오기</button>}</span>;
  if (!current?.url) return <span role="status">이미지를 불러오는 중이에요…</span>;
  // eslint-disable-next-line @next/next/no-img-element
  return <img className={className} src={current.url} alt={alt} referrerPolicy="no-referrer"
    onError={() => setState({ path: accessPath, url: "", error: true })} />;
}
