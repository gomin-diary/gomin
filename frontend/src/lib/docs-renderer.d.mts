import type { ElementType, ReactElement } from "react";
export function MarkdownContent(props: {
  markdown: string;
  source: string;
  documents: { source: string; url: string }[];
  Diagram: ElementType<{ code: string }>;
}): ReactElement;
