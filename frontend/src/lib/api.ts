import type { ApiError, ApiResponse, ErrorDetail } from "./api-types";

const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL;

// Capture the session generation before sending a request so a late 401 cannot
// invalidate a newer login. Auth endpoints handle their own failures.
const authFailureListeners = new Set<() => () => void>();
export function subscribeAuthFailure(capture: () => () => void): () => void {
  authFailureListeners.add(capture);
  return () => { authFailureListeners.delete(capture); };
}

export class ApiRequestError extends Error {
  readonly status: number | null;
  readonly code: string;
  readonly details: ErrorDetail[];

  constructor(status: number | null, error: ApiError) {
    super(error.message);
    this.name = "ApiRequestError";
    this.status = status;
    this.code = error.code;
    this.details = error.details;
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isErrorDetail(value: unknown): value is ErrorDetail {
  return isRecord(value) && Array.isArray(value.path)
    && value.path.every((part: unknown) => typeof part === "string" || (typeof part === "number" && Number.isInteger(part)))
    && typeof value.code === "string" && value.code.length > 0
    && typeof value.message === "string";
}

function isApiResponse(value: unknown): value is ApiResponse<unknown> {
  if (!isRecord(value)) return false;
  if (value.success === true) return Object.hasOwn(value, "data") && value.error === null;
  if (value.success !== false || value.data !== null || !isRecord(value.error)) return false;
  return typeof value.error.code === "string" && value.error.code.length > 0
    && typeof value.error.message === "string"
    && Array.isArray(value.error.details) && value.error.details.every(isErrorDetail);
}

function isAbort(error: unknown): boolean {
  return isRecord(error) && error.name === "AbortError";
}

function invalidResponse(status: number): ApiRequestError {
  return new ApiRequestError(status, {
    code: "INVALID_RESPONSE", message: "서버 응답 형식이 올바르지 않습니다.", details: [],
  });
}

/** JSON APIs only. T describes data; it does not validate endpoint data at runtime. */
export async function apiFetch<T = unknown>(path: string, init?: RequestInit): Promise<T> {
  const authRequest = path.startsWith("/api/v1/auth/");
  const protectedRequest = path.startsWith("/api/v1/") && !authRequest;
  const notifyUnauthorized = protectedRequest ? [...authFailureListeners].map((capture) => capture()) : [];
  if (!apiBaseUrl) throw new Error("NEXT_PUBLIC_API_BASE_URL is not configured");
  if (!path.startsWith("/") || path.startsWith("//")) {
    throw new Error("API paths must start with a single slash");
  }

  let response: Response;
  try {
    const url = `${apiBaseUrl.replace(/\/$/, "")}${path}`;
    response = await fetch(url, { ...init, cache: "no-store", ...(authRequest || protectedRequest ? { credentials: "include" } : {}) });
  } catch (error) {
    if (isAbort(error)) throw error;
    throw new ApiRequestError(null, {
      code: "NETWORK_ERROR", message: "서버에 연결할 수 없습니다.", details: [],
    });
  }

  let body: unknown;
  if (response.status === 401) notifyUnauthorized.forEach((notify) => notify());
  try {
    body = await response.json();
  } catch (error) {
    if (isAbort(error)) throw error;
    throw invalidResponse(response.status);
  }
  if (!isApiResponse(body) || response.ok !== body.success) throw invalidResponse(response.status);
  if (!body.success) throw new ApiRequestError(response.status, body.error);
  return body.data as T;
}
