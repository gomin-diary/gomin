import assert from "node:assert/strict";
import { test } from "node:test";
import { createMockCollectionRepository, createCollectionController, CollectionNotFoundError, visibleCollectionItems } from "../src/lib/collection.ts";
import { collectionFixtures } from "../src/lib/collection-fixtures.ts";

const owner = "00000000-0000-4000-8000-000000000001";
const other = "00000000-0000-4000-8000-000000000002";
const newMember = "54ab12cd-6ec4-4a51-9bb5-4ddfc8806a23";
const repository = (scenario = "normal") => createMockCollectionRepository(collectionFixtures, { scenario, delay: 0 });
const deferred = () => { let resolve, reject; const promise = new Promise((yes, no) => { resolve = yes; reject = no; }); return { promise, resolve, reject }; };

test("all signed-in members receive the same demo list and matching details", async () => {
  const repo = repository();
  const mine = await repo.list(owner);
  assert.equal(mine.length, 8);
  assert.deepEqual(await repo.list(other), mine);
  assert.deepEqual(await repo.list("00000000-0000-4000-8000-000000000003"), mine);
  assert.deepEqual(await repo.list(newMember), mine);
  assert.deepEqual(await repo.list(""), []);
  for (const item of mine) {
    const detail = await repo.detail(owner, item.id);
    assert.equal(detail.title, item.title);
    assert.equal(detail.date, item.date);
    assert.ok(detail.mind);
    assert.ok(!Object.hasOwn(detail, "memberId"));
    assert.deepEqual(await repo.detail(other, item.id), detail);
    assert.deepEqual(await repo.detail(newMember, item.id), detail);
  }
  await assert.rejects(repo.detail(owner, "missing"), CollectionNotFoundError);
  await assert.rejects(repo.detail("", mine[0].id), CollectionNotFoundError);
  mine[0].title = "modified";
  assert.notEqual((await repo.list(owner))[0].title, "modified");
});

test("six-frame navigation clamps at both ends and closing detail preserves page/filter", async () => {
  const controller = createCollectionController(owner, repository());
  await controller.load();
  controller.move(-1);
  assert.equal(controller.getSnapshot().page, 0);
  controller.move(1); controller.move(1);
  assert.equal(controller.getSnapshot().page, 1);
  await controller.select("local-1-7");
  assert.equal(controller.getSnapshot().detail.id, "local-1-7");
  controller.close();
  assert.equal(controller.getSnapshot().page, 1);
  assert.equal(controller.getSnapshot().detail, null);
  controller.filter("관계");
  assert.equal(controller.getSnapshot().page, 0);
  assert.ok(visibleCollectionItems(controller.getSnapshot()).every((item) => item.categories.includes("관계")));
  await controller.select(visibleCollectionItems(controller.getSnapshot())[0].id);
  controller.close();
  assert.equal(controller.getSnapshot().category, "관계");
});

test("empty success differs from list error and retry recovers", async () => {
  const emptyController = createCollectionController(owner, repository("empty"));
  await emptyController.load();
  assert.equal(emptyController.getSnapshot().status, "ready");
  assert.deepEqual(emptyController.getSnapshot().items, []);
  const failed = createCollectionController(owner, repository("error"));
  const loading = failed.load();
  assert.equal(failed.getSnapshot().status, "loading");
  await loading;
  assert.equal(failed.getSnapshot().status, "error");
  await failed.load();
  assert.equal(failed.getSnapshot().status, "ready");
  assert.equal(failed.getSnapshot().items.length, 8);
});

test("detail error, retry and not-found remain distinct from an empty list", async () => {
  const controller = createCollectionController(owner, repository("detail-error"));
  await controller.load();
  await controller.select("local-1-1");
  assert.equal(controller.getSnapshot().detailStatus, "error");
  assert.equal(controller.getSnapshot().detailNotFound, false);
  await controller.select("local-1-1");
  assert.equal(controller.getSnapshot().detailStatus, "ready");
  await controller.select("missing");
  assert.equal(controller.getSnapshot().detailNotFound, true);
  assert.equal(controller.getSnapshot().items.length, 8);
});

test("late list responses cannot replace a retry, or publish after account disposal", async () => {
  let pending = [];
  const controller = createCollectionController(owner, { ...repository(), list: () => { const request = deferred(); pending.push(request); return request.promise; } });
  const first = controller.load(), second = controller.load();
  pending[1].resolve([collectionFixtures[1]]); await second;
  pending[0].resolve([collectionFixtures[0]]); await first;
  assert.equal(controller.getSnapshot().items[0].id, "local-1-2");
  const third = controller.load();
  controller.dispose();
  const snapshot = controller.getSnapshot();
  pending[2].resolve([collectionFixtures[0]]); await third;
  assert.equal(controller.getSnapshot(), snapshot);
});

test("rapid selection, closing and disposal discard delayed detail success/failure", async () => {
  let pending = [];
  const controller = createCollectionController(owner, { ...repository(), detail: () => { const request = deferred(); pending.push(request); return request.promise; } });
  const first = controller.select("local-1-1"), second = controller.select("local-1-2");
  pending[1].resolve(collectionFixtures[1]); await second;
  pending[0].reject(new Error("late")); await first;
  assert.equal(controller.getSnapshot().detail.id, "local-1-2");
  const third = controller.select("local-1-3"); controller.close();
  pending[2].resolve(collectionFixtures[2]); await third;
  assert.equal(controller.getSnapshot().selectedId, null);
  assert.equal(controller.getSnapshot().detail, null);
  const fourth = controller.select("local-1-4"); controller.dispose();
  const snapshot = controller.getSnapshot();
  pending[3].resolve(collectionFixtures[3]); await fourth;
  assert.equal(controller.getSnapshot(), snapshot);
});
