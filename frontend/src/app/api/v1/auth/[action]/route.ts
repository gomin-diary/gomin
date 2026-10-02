import { NextRequest } from "next/server";
import { forwardAuthRequest } from "@/lib/auth-proxy";

export const dynamic = "force-dynamic";
async function proxy(request: NextRequest, context: { params: Promise<{ action: string }> }) {
  return forwardAuthRequest(request, (await context.params).action);
}
export const GET = proxy;
export const POST = proxy;
