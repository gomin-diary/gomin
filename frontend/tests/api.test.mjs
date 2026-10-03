import assert from "node:assert/strict";
import { after, test } from "node:test";

process.env.NEXT_PUBLIC_API_BASE_URL = "https://api.example.test/";
const { apiFetch } = await import("../src/lib/api.ts");
const originalFetch = globalThis.fetch;
after(() => { globalThis.fetch = originalFetch; });

function respond(body, status = 200) {
  globalThis.fetch = async () => Response.json(body, { status });
}

test("returns success data and keeps path, init and no-store behavior", async () => {
  globalThis.fetch = async (url, init) => {
    assert.equal(url, "https://api.example.test/api/v1/health");
    assert.equal(init.cache, "no-store");
    assert.equal(init.method, "GET");
    return Response.json({ success: true, data: { status: "ok" }, error: null });
  };
  assert.deepEqual(await apiFetch("/api/v1/health", { method: "GET", cache: "force-cache" }), { status: "ok" });
});

test("preserves server status, code and field errors", async () => {
  const details = [{ path: ["body", "items", 0], code: "INVALID_FORMAT", message: "Invalid input" }];
  respond({ success: false, data: null, error: { code: "VALIDATION_ERROR", message: "Check input", details } }, 422);
  await assert.rejects(apiFetch("/api/v1/example"), (error) => {
    assert.equal(error.name, "ApiRequestError");
    assert.equal(error.status, 422);
    assert.equal(error.code, "VALIDATION_ERROR");
    assert.deepEqual(error.details, details);
    return true;
  });
});

test("rejects malformed envelopes and HTTP/body contradictions", async () => {
  for (const [body, status] of [
    [{ status: "ok" }, 200],
    [{ success: true, data: {}, error: null }, 503],
    [{ success: false, data: null, error: { code: "FAIL", message: "Failed", details: [] } }, 200],
    [{ success: true, error: null }, 200],
    [{ success: true, data: {}, error: {} }, 200],
    [{ success: false, data: null, error: { code: "FAIL", message: "Failed", details: [{ path: [null] }] } }, 400],
  ]) {
    respond(body, status);
    await assert.rejects(apiFetch("/api/v1/example"), (error) => error.code === "INVALID_RESPONSE" && error.status === status);
  }
});

test("non-JSON and empty responses are invalid", async () => {
  for (const response of [new Response("<html>unavailable</html>", { status: 502 }), new Response(null, { status: 204 })]) {
    globalThis.fetch = async () => response;
    await assert.rejects(apiFetch("/api/v1/example"), (error) => error.code === "INVALID_RESPONSE");
  }
});

test("network failures are distinct from server errors", async () => {
  globalThis.fetch = async () => { throw new TypeError("connection failed"); };
  await assert.rejects(apiFetch("/api/v1/example"), (error) => error.code === "NETWORK_ERROR" && error.status === null);
});

test("preserves cancellation during fetch and body reading", async () => {
  const abort = new DOMException("Cancelled", "AbortError");
  globalThis.fetch = async () => { throw abort; };
  await assert.rejects(apiFetch("/api/v1/example"), (error) => error === abort);
  globalThis.fetch = async () => ({ ok: true, status: 200, json: async () => { throw abort; } });
  await assert.rejects(apiFetch("/api/v1/example"), (error) => error === abort);
});

test("rejects paths that could escape the configured API base", async () => {
  for (const path of ["https://example.test/", "//example.test/", "relative"]) {
    await assert.rejects(apiFetch(path), /single slash/);
  }
});

test("all auth requests call the backend directly and include cookies", async () => {
  for (const [action, method] of [
    ["me", "GET"], ["login", "POST"], ["logout", "POST"], ["signup", "POST"],
    ["email-verifications", "POST"], ["email-verifications/confirm", "POST"],
  ]) {
    const body = method === "POST" ? JSON.stringify({ email: "member@example.test" }) : undefined;
    globalThis.fetch = async (url, init) => {
      assert.equal(url, `https://api.example.test/api/v1/auth/${action}`);
      assert.equal(init.credentials, "include");
      assert.equal(init.cache, "no-store");
      assert.equal(init.method, method);
      assert.equal(init.body, body);
      return Response.json({ success: true, data: { id: "member-id" }, error: null });
    };
    assert.deepEqual(await apiFetch(`/api/v1/auth/${action}`, {
      method, body, credentials: "omit",
    }), { id: "member-id" });
  }
});
