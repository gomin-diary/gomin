import assert from "node:assert/strict";
import { test } from "node:test";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { MarkdownContent } from "../src/lib/docs-renderer.mjs";

const document = { source: "docs/README.md", url: "/docs" };
const linked = { source: "docs/setup/README.md", url: "/docs/setup" };
function render(markdown) {
  return renderToStaticMarkup(createElement(MarkdownContent, { markdown, source: document.source, documents: [document, linked], Diagram: ({ code }) => createElement("pre", { "data-diagram": true }, code) }));
}
test("Markdown output rewrites nested document links and retains heading anchors", () => {
  const html = render("# 문서\n\n## 제목 **하나**\n\n## 제목 **하나**\n\n[설치](setup/README.md?from=index#설치)");
  assert.match(html, /id="제목-하나"/);
  assert.match(html, /id="제목-하나-1"/);
  const href = html.match(/href="([^"]+)"/)?.[1];
  assert.equal(decodeURI(href), "/docs/setup?from=index#설치");
});
test("GFM tables and code render while raw HTML and executable links are blocked", () => {
  const html = render("| 항목 | 값 |\n| --- | --- |\n| 기능 | 문서 |\n\n```sh\nnpm run dev\n```\n\n<script>alert(1)</script>\n\n[위험](javascript:alert%281%29)");
  assert.match(html, /<table>/);
  assert.match(html, /language-sh/);
  assert.ok(!html.includes("<script>"));
  assert.ok(!html.includes('href="javascript:'));
});
test("Mermaid blocks keep source available through the diagram component", () => {
  const html = render("```mermaid\nflowchart LR\n A --> B\n```");
  assert.match(html, /data-diagram="true"/);
  assert.match(html, /flowchart LR/);
  assert.match(html, /A --&gt; B/);
});

test("repository source links point to GitHub without serving source files", () => {
  const html = render("[API](../backend/app/main.py#L10) [워크플로](../.github/workflows/check.yml) [비공개](../frontend/.env.local)");
  assert.match(html, /href="https:\/\/github.com\/gomin-diary\/gomin\/blob\/main\/backend\/app\/main.py#L10"/);
  assert.match(html, /href="https:\/\/github.com\/gomin-diary\/gomin\/blob\/main\/\.github\/workflows\/check.yml"/);
  assert.ok(!html.includes('href="../frontend/.env.local"'));
  assert.ok(!html.includes('blob/main/frontend/.env.local'));
});

test("footnote references retain their accessible label and return link alongside document heading IDs", () => {
  const html = render("# API\n\nOpenAPI[^openapi]\n\n## 다음 내용\n\n본문\n\n[^openapi]: API 사용법을 기록하는 공통 규칙.");
  assert.match(html, /id="다음-내용"/);
  assert.match(html, /<h2[^>]*id="footnote-label"[^>]*>각주<\/h2>/);
  assert.match(html, /href="#user-content-fn-openapi"[^>]*id="user-content-fnref-openapi"[^>]*aria-describedby="footnote-label"/);
  assert.match(html, /<li id="user-content-fn-openapi">/);
  assert.match(html, /href="#user-content-fnref-openapi"[^>]*aria-label="본문으로 돌아가기"/);
});
