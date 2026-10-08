import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { test } from "node:test";
import ts from "typescript";

// Compile only the adapter; use its injectable request to avoid a live backend.
const source = await readFile(new URL("../src/lib/collection-api.ts", import.meta.url), "utf8");
let output = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.ESNext } }).outputText;
for (const name of ["api", "collection"]) {
  output = output.replaceAll(`"./${name}"`, JSON.stringify(new URL(`../src/lib/${name}.ts`, import.meta.url).href));
}
const { createApiCollectionRepository } = await import(`data:text/javascript;base64,${Buffer.from(output).toString("base64")}`);
const row = { id: "entry-id", source_result_id: "result-id", title: "오늘의 기록", diary_date: "2026-10-08",
  emotion_tags: ["불안", "낯선 감정"], image_url: "https://example.test/private-image" };

test("real list maps entry IDs and signed images without trusting a client member ID", async () => {
  const signal = new AbortController().signal;
  const repo = createApiCollectionRepository(async (path, init) => {
    assert.equal(path, "/api/v1/collection");
    assert.equal(init.signal, signal);
    return [row];
  });
  const [item] = await repo.list("untrusted-member-id", signal);
  assert.equal(item.id, row.id);
  assert.deepEqual(item.image, { src: row.image_url, width: 1, left: 0, top: 0 });
  assert.deepEqual(item.categories, ["불안"]);
});

test("real list preserves empty success and propagates failures", async () => {
  assert.deepEqual(await createApiCollectionRepository(async () => []).list("member"), []);
  await assert.rejects(createApiCollectionRepository(async () => { throw new Error("offline"); }).list("member"), /offline/);
});
