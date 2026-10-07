"use client";

import { useEffect, useId, useState } from "react";

let engine: Promise<typeof import("mermaid")> | undefined;

function loadMermaid() {
  engine ??= import("mermaid").then(module => {
    module.default.initialize({
      startOnLoad: false,
      securityLevel: "strict",
      suppressErrorRendering: true,
      fontFamily: "system-ui, sans-serif",
      flowchart: { htmlLabels: false, useMaxWidth: false },
      er: { useMaxWidth: false },
    });
    return module;
  });
  return engine;
}

export function MermaidDiagram({ code }: { code: string }) {
  const id = useId().replace(/[^a-zA-Z0-9_-]/g, "");
  const [result, setResult] = useState<{ svg: string; failed: boolean }>({ svg: "", failed: false });
  useEffect(() => {
    let active = true;
    void loadMermaid()
      .then(module => module.default.render(`docs-diagram-${id}`, code))
      .then(({ svg }) => { if (active) setResult({ svg, failed: false }); })
      .catch(() => { if (active) setResult({ svg: "", failed: true }); });
    return () => { active = false; };
  }, [code, id]);

  return <figure className="docs-diagram">
    {result.svg ? <div role="img" aria-label="문서 도표" dangerouslySetInnerHTML={{ __html: result.svg }} /> : null}
    {result.failed ? <p role="status">도표를 표시할 수 없습니다. 원본 코드를 확인해 주세요.</p> : null}
    <details open={!result.svg}>
      <summary>도표 원본 코드</summary>
      <pre><code>{code}</code></pre>
    </details>
  </figure>;
}
