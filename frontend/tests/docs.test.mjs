import assert from "node:assert/strict";
import { test } from "node:test";
import { mkdtemp, mkdir, writeFile, symlink, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import { buildDocumentation } from "../scripts/generate-docs.mjs";
import { analyzeMarkdown, documentUrl, resolveDocumentLink } from "../src/lib/docs-markdown.mjs";

async function fixture(files, run) {
  const root = await mkdtemp(path.join(tmpdir(), "gomin-docs-"));
  try {
    for (const [name, text] of Object.entries(files)) {
      await mkdir(path.dirname(path.join(root, name)), { recursive: true });
      await writeFile(path.join(root, name), text);
    }
    await run(root);
  } finally { await rm(root, { recursive: true, force: true }); }
}

test("index order and recursive links produce one document per URL", async () => {
  await fixture({
    "docs/README.md": "# 문서\n\n## 개발\n- [두 번째](guide/README.md)\n- [첫 번째][first]\n\n[first]: first.md\n",
    "docs/guide/README.md": "# 설치\n[상세](detail.md)\n[목록](../README.md)",
    "docs/guide/detail.md": "# 상세\n[첫 문서](../first.md)",
    "docs/first.md": "# 첫 문서\n[설치](guide/README.md)",
    "docs/unlisted.md": "# 목록 밖",
  }, async (root) => {
    const result = await buildDocumentation(root);
    assert.deepEqual(result.documents.map(d => d.url), ["/docs", "/docs/guide", "/docs/first", "/docs/guide/detail"]);
    assert.deepEqual(result.navigation, [{ title: "개발", items: [{ title: "두 번째", url: "/docs/guide" }, { title: "첫 번째", url: "/docs/first" }] }]);
  });
});

test("relative links retain fragments and query with README folder URLs", () => {
  assert.equal(documentUrl("docs/README.md"), "/docs");
  assert.equal(documentUrl("docs/setup/README.md"), "/docs/setup");
  assert.equal(documentUrl("README.md"), "/docs/project-readme");
  assert.deepEqual(resolveDocumentLink("docs/setup/windows.md", "../login.md?view=all#로그인"), { source: "docs/login.md", query: "?view=all", fragment: "#로그인" });
  assert.equal(resolveDocumentLink("docs/README.md", "https://example.com/page.md"), null);
  assert.equal(resolveDocumentLink("docs/README.md", "#목차"), null);
  assert.throws(() => resolveDocumentLink("docs/README.md", "superpowers/plans/private.md"), /Excluded/);
  assert.throws(() => resolveDocumentLink("docs/README.md", "../backend/secret.md"), /Outside/);
  assert.throws(() => resolveDocumentLink("docs/README.md", "%2e%2e/%2e%2e/secret.md"), /Outside/);
  assert.throws(() => resolveDocumentLink("docs/README.md", ".env.md"), /Excluded/);
  assert.throws(() => resolveDocumentLink("docs/README.md", "folder%5C..%5Csuperpowers%5Cplans%5Cprivate.md"), /Backslash/);
  assert.throws(() => documentUrl("docs/folder\\..\\private.md"), /Backslash/);
});

test("heading anchors follow Korean, formatted and duplicate titles", () => {
  const { headings } = analyzeMarkdown("# 제목\n\n## 로그인 **설정**\n\n## 로그인 **설정**\n\n### A & B\n\n```md\n## 코드 제목\n```");
  assert.deepEqual(headings, [
    { depth: 1, text: "제목", id: "제목" },
    { depth: 2, text: "로그인 설정", id: "로그인-설정" },
    { depth: 2, text: "로그인 설정", id: "로그인-설정-1" },
    { depth: 3, text: "A & B", id: "a--b" },
  ]);
});

test("missing local links fail with source paths", async () => {
  await fixture({ "docs/README.md": "# 문서\n[누락](missing.md)" }, async root => {
    await assert.rejects(buildDocumentation(root), /docs\/missing.md/);
  });
});

test("symlinks cannot expose a file outside the document root", async () => {
  await fixture({ "docs/README.md": "# 문서\n[링크](leak.md)", "private.md": "# 비공개" }, async root => {
    await symlink(path.join(root, "private.md"), path.join(root, "docs/leak.md"));
    await assert.rejects(buildDocumentation(root), /Symlink/);
  });
});

test("colliding README and file routes fail rather than shadow a document", async () => {
  await fixture({ "docs/README.md": "[설치](setup.md) [폴더](setup/README.md)", "docs/setup.md": "# 설치", "docs/setup/README.md": "# 폴더" }, async root => {
    await assert.rejects(buildDocumentation(root), /Duplicate/);
  });
});
