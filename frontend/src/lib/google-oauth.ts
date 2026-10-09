type RoutingStorage = Pick<Storage, "getItem" | "setItem" | "removeItem">;
type Context = { origin: "/login" | "/signup"; next: string };
const KEY = "gomin.google.navigation";
const destinations = ["/", "/talk", "/collection", "/settings"];
const fallback: Context = { origin: "/login", next: "/" };

export function safeLoginDestination(next: unknown): string {
  if (typeof next !== "string") return "/";
  const uuid = "[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}";
  return destinations.includes(next) || new RegExp(`^/talk/${uuid}(?:/handoff/${uuid})?$`).test(next)
    || new RegExp(`^/talk\\?summary=${uuid}$`).test(next) ? next : "/";
}

export function saveGoogleContext(storage: RoutingStorage | null, origin: string, next: string | null) {
  try {
    storage?.setItem(KEY, JSON.stringify({ origin: origin === "/signup" ? "/signup" : "/login", next: safeLoginDestination(next) }));
  } catch { /* Navigation still works when browser storage is unavailable. */ }
}
export function readGoogleContext(storage: RoutingStorage | null): Context {
  try {
    const value = JSON.parse(storage?.getItem(KEY) ?? "null");
    return { origin: value?.origin === "/signup" ? "/signup" : "/login", next: safeLoginDestination(value?.next) };
  } catch { return { ...fallback }; }
}
export function clearGoogleContext(storage: RoutingStorage | null) {
  try { storage?.removeItem(KEY); } catch { /* Storage can be blocked. */ }
}
export function browserRoutingStorage(): RoutingStorage | null {
  try { return window.sessionStorage; } catch { return null; }
}
export function googleAuthorizationUrl(value: unknown) {
  const message = "Google 로그인 주소를 확인할 수 없어요. 다시 시도해 주세요.";
  if (typeof value !== "string") throw new Error(message);
  const url = new URL(value);
  if (url.origin !== "https://accounts.google.com" || url.pathname !== "/o/oauth2/v2/auth" || url.username || url.password || url.hash) throw new Error(message);
  return url.toString();
}
export function googleOAuthNotice(code: string | undefined) {
  if (!code) return "";
  const messages: Record<string, string> = {
    OAUTH_REQUEST_INVALID: "인증 요청이 만료됐어요. Google 로그인을 다시 시작해 주세요.",
    OAUTH_PROOF_INVALID: "가입 인증이 만료됐어요. Google 로그인을 다시 시작해 주세요.",
    OAUTH_LINK_CONFLICT: "이미 연결된 Google 계정을 확인해 주세요.",
    EMAIL_EXISTS: "이미 가입된 이메일이에요. Google 로그인을 다시 시작해 주세요.",
    OAUTH_NOT_CONFIGURED: "Google 로그인을 준비하고 있어요.",
  };
  return Object.hasOwn(messages, code) ? messages[code] : "Google 인증에 실패했어요. 다시 시도해 주세요.";
}
export type GooglePending = { email: string; profile_name: string | null; expires_at: string; csrf_token: string };
