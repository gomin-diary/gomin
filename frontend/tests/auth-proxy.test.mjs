import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { createRequire } from "node:module";
import { pathToFileURL } from "node:url";
import { after, test } from "node:test";
import ts from "typescript";

// Node does not resolve Next's extensionless ESM import. Transpile the actual module
// and resolve only that package import; the production proxy logic is unchanged.
const require = createRequire(import.meta.url);
const serverUrl = pathToFileURL(require.resolve("next/server")).href;
const { NextRequest } = await import(serverUrl);
const source = await readFile(new URL("../src/lib/auth-proxy.ts", import.meta.url), "utf8");
const output = ts.transpileModule(source.replace('"next/server"', JSON.stringify(serverUrl)), {
  compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 },
}).outputText;
const { forwardAuthRequest } = await import(`data:text/javascript;base64,${Buffer.from(output).toString("base64")}`);
const originalFetch = globalThis.fetch;
after(() => { globalThis.fetch = originalFetch; });
process.env.NEXT_PUBLIC_API_BASE_URL = "https://api.example.test/";

function request(action, method = "POST", cookie = "") {
  return new NextRequest(`https://frontend.example.test/api/v1/auth/${action}`, {
    method, headers: { Cookie: cookie, "Content-Type": "application/json", Authorization: "unrelated-private-value" },
    ...(method === "POST" ? { body: JSON.stringify({ email: "member@example.com" }) } : {}),
  });
}

test("proxy forwards body and only service session cookie, then preserves Set-Cookie", async () => {
  const token = "a".repeat(43);
  globalThis.fetch = async (url, init) => {
    assert.equal(url, "https://api.example.test/api/v1/auth/signup");
    assert.equal(init.headers.get("Cookie"), `gomin_session=${token}`);
    assert.equal(init.headers.get("Authorization"), null);
    assert.equal(init.cache, "no-store");
    assert.equal(init.redirect, "error");
    assert.deepEqual(JSON.parse(init.body), { email: "member@example.com" });
    return Response.json({ success: true, data: { id: "member" }, error: null }, {
      status: 201, headers: { "Set-Cookie": `gomin_session=${token}; HttpOnly; SameSite=Lax; Path=/` },
    });
  };
  const response = await forwardAuthRequest(request("signup", "POST", `other_cookie=private-value; gomin_session=${token}`), "signup");
  assert.equal(response.status, 201);
  assert.match(response.headers.get("Set-Cookie"), /HttpOnly/);
  assert.equal(response.headers.get("Cache-Control"), "no-store");
});

test("nested email confirmation is supported and malformed cookies are dropped", async () => {
  globalThis.fetch = async (url, init) => {
    assert.equal(url, "https://api.example.test/api/v1/auth/email-verifications/confirm");
    assert.equal(init.headers.get("Cookie"), null);
    return Response.json({ success: false, data: null, error: { code: "CODE_MISMATCH", message: "Mismatch", details: [] } }, { status: 400 });
  };
  const response = await forwardAuthRequest(request("email-verifications/confirm", "POST", "gomin_session=invalid"), "email-verifications/confirm");
  assert.equal(response.status, 400);
  assert.equal((await response.json()).error.code, "CODE_MISMATCH");
});

test("proxy rejects arbitrary actions and wrong methods without upstream access", async () => {
  globalThis.fetch = async () => { throw new Error("must not fetch"); };
  for (const [action, method] of [["admin", "POST"], ["signup", "GET"], ["me", "POST"]]) {
    assert.equal((await forwardAuthRequest(request(action, method), action)).status, 404);
  }
});

test("proxy converts transport failure to sanitized common error response", async () => {
  globalThis.fetch = async () => { throw new Error("private-credential"); };
  const response = await forwardAuthRequest(request("signup"), "signup");
  assert.equal(response.status, 503);
  const body = await response.text();
  assert.equal(JSON.parse(body).error.code, "SERVICE_UNAVAILABLE");
  assert.ok(!body.includes("private-credential"));
});
