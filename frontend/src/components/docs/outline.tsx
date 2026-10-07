"use client";

import { useEffect, useRef } from "react";

export function DocOutline({ title, children }: { title: string; children: React.ReactNode }) {
  const details = useRef<HTMLDetailsElement>(null);
  useEffect(() => {
    const media = window.matchMedia("(min-width: 768px)");
    const update = () => { if (details.current) details.current.open = media.matches; };
    update();
    media.addEventListener("change", update);
    return () => media.removeEventListener("change", update);
  }, []);
  return <details ref={details} open><summary>{title}</summary>{children}</details>;
}
