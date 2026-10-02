import { NextRequest } from "next/server";
import { forwardAuthRequest } from "@/lib/auth-proxy";

export const dynamic = "force-dynamic";
export async function POST(request: NextRequest) {
  return forwardAuthRequest(request, "email-verifications/confirm");
}
