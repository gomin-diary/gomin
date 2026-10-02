import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";

async function proxy(request: NextRequest, context: { params: Promise<{ action: string }> }) {
  const { action } = await context.params;
  if (!((action === "me" && request.method === "GET") ||
        ((action === "login" || action === "logout") && request.method === "POST"))) {
    return NextResponse.json({ success: false, data: null, error: {
      code: "NOT_FOUND", message: "요청한 대상을 찾을 수 없습니다.", details: [],
    } }, { status: 404 });
  }
  try {
    const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL;
    if (!baseUrl) throw new Error("API URL is not configured");
    const headers = new Headers({ "Content-Type": "application/json" });
    // Forward only this service's session cookie, never unrelated web cookies.
    const token = request.cookies.get("gomin_session")?.value;
    if (token && /^[A-Za-z0-9_-]{43}$/.test(token)) headers.set("Cookie", `gomin_session=${token}`);
    const upstream = await fetch(`${baseUrl.replace(/\/$/, "")}/api/v1/auth/${action}`, {
      method: request.method, headers, cache: "no-store", redirect: "error",
      body: request.method === "POST" ? await request.text() : undefined,
      signal: AbortSignal.timeout(15000),
    });
    const response = new NextResponse(await upstream.text(), { status: upstream.status,
      headers: { "Content-Type": "application/json", "Cache-Control": "no-store" } });
    for (const cookie of upstream.headers.getSetCookie()) response.headers.append("Set-Cookie", cookie);
    return response;
  } catch {
    return NextResponse.json({ success: false, data: null, error: {
      code: "SERVICE_UNAVAILABLE", message: "인증 서버에 연결할 수 없습니다. 잠시 후 다시 시도해 주세요.", details: [],
    } }, { status: 503, headers: { "Cache-Control": "no-store" } });
  }
}

export const GET = proxy;
export const POST = proxy;
