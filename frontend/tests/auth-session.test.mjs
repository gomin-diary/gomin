import assert from "node:assert/strict";
import { test } from "node:test";
import { createAuthSession, AUTH_RECHECK_MS } from "../src/lib/auth-session.ts";

const member = { id: "one", email: "one@example.test", name: "One" };
const unauthorized = { status: 401 };
const isUnauthorized = (error) => error === unauthorized;
function deferred() {
  let resolve, reject;
  const promise = new Promise((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
}

test("initial verification, fresh cache, stale return and concurrent retries", async () => {
  let time = 0, calls = 0;
  let response = deferred();
  const session = createAuthSession(() => { calls++; return response.promise; }, isUnauthorized, () => time);
  assert.equal(session.getSnapshot().member, undefined);
  const first = session.recheck();
  assert.equal(session.refresh(), first);
  response.resolve(member);
  await first;
  time = AUTH_RECHECK_MS - 1;
  await session.recheck();
  assert.equal(calls, 1);
  time++;
  response = deferred();
  const next = session.recheck();
  assert.equal(session.recheck(), next);
  assert.equal(calls, 2);
  response.resolve(member);
  await next;
});

test("initial failure remains unknown, cached failure preserves user, retry recovers", async () => {
  let fail = true;
  const session = createAuthSession(async () => { if (fail) throw new Error("503/network"); return member; }, isUnauthorized);
  await session.refresh();
  assert.equal(session.getSnapshot().member, undefined);
  assert.ok(session.getSnapshot().error);
  session.accept(member);
  await session.refresh();
  assert.equal(session.getSnapshot().member, member);
  assert.ok(session.getSnapshot().error);
  fail = false;
  await session.refresh();
  assert.equal(session.getSnapshot().error, "");
});

test("401 clears cache; previous lookup cannot restore an invalidated session", async () => {
  const response = deferred();
  const session = createAuthSession(() => response.promise, isUnauthorized);
  session.accept(member);
  const request = session.refresh();
  session.captureUnauthorized()();
  response.resolve(member);
  await request;
  assert.equal(session.getSnapshot().member, null);
  const expired = createAuthSession(async () => { throw unauthorized; }, isUnauthorized);
  expired.accept(member);
  await expired.refresh();
  assert.equal(expired.getSnapshot().member, null);
});

test("late lookup and protected 401 cannot overwrite a newer login or logout", async () => {
  for (const value of [member, null]) {
    const response = deferred();
    const session = createAuthSession(() => response.promise, isUnauthorized);
    const oldUnauthorized = session.captureUnauthorized();
    const request = session.refresh();
    session.accept(value);
    response.reject(unauthorized);
    oldUnauthorized();
    await request;
    assert.equal(session.getSnapshot().member, value);
    assert.equal(session.getSnapshot().error, "");
  }
});

test("login response avoids immediate lookup; invalidation preserves failed logout state", async () => {
  let calls = 0;
  const session = createAuthSession(async () => { calls++; return member; }, isUnauthorized);
  session.accept(member);
  await session.recheck();
  assert.equal(calls, 0);
  const oldUnauthorized = session.captureUnauthorized();
  session.invalidate();
  oldUnauthorized();
  assert.equal(session.getSnapshot().member, member);
});
