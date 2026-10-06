import { apiFetch } from "./api";

interface UploadGrant {
  bucket: string;
  path: string;
  upload_url: string;
  expires_in: number;
  max_file_size_bytes: number;
}

export interface UploadedFile {
  bucket: string;
  path: string;
  filename: string;
  size: number;
  content_type: string;
}

export class FileUploadError extends Error {
  readonly code: string;
  readonly status: number | null;
  readonly upload_uncertain: boolean;

  constructor(code: string, message: string, status: number | null = null, uploadUncertain = false) {
    super(message);
    this.name = "FileUploadError";
    this.code = code;
    this.status = status;
    this.upload_uncertain = uploadUncertain;
  }
}

function isGrant(value: unknown): value is UploadGrant {
  if (!value || typeof value !== "object") return false;
  const grant = value as Record<string, unknown>;
  if (typeof grant.bucket !== "string" || !/^[A-Za-z0-9][A-Za-z0-9_-]{0,99}$/.test(grant.bucket)
    || typeof grant.path !== "string" || !/^[0-9a-f-]{36}\/[0-9a-f-]{36}$/.test(grant.path)
    || typeof grant.upload_url !== "string"
    || !Number.isSafeInteger(grant.expires_in) || (grant.expires_in as number) <= 0
    || !Number.isSafeInteger(grant.max_file_size_bytes) || (grant.max_file_size_bytes as number) <= 0) return false;
  try {
    const url = new URL(grant.upload_url);
    const localHttp = url.protocol === "http:" && ["localhost", "127.0.0.1", "[::1]"].includes(url.hostname);
    return (url.protocol === "https:" || localHttp) && !url.username && !url.password && !url.hash
      && url.pathname.endsWith(`/storage/v1/object/upload/sign/${grant.bucket}/${grant.path}`)
      && Boolean(url.searchParams.get("token"));
  } catch {
    return false;
  }
}

/** Mint with the app session, then send bytes directly to Storage. Never automatically retry. */
export async function uploadFile(file: File, options: { signal?: AbortSignal } = {}): Promise<UploadedFile> {
  if (!Number.isSafeInteger(file.size) || file.size <= 0 || !file.name.trim()) {
    throw new FileUploadError("INVALID_FILE", "내용이 있는 파일을 선택해 주세요.");
  }
  const contentType = file.type || "application/octet-stream";
  const grant = await apiFetch<unknown>("/api/v1/files/upload-url", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ filename: file.name, size: file.size, content_type: contentType }),
    signal: options.signal,
  });
  if (!isGrant(grant)) {
    throw new FileUploadError("INVALID_RESPONSE", "업로드 URL 응답 형식이 올바르지 않습니다.");
  }
  if (file.size > grant.max_file_size_bytes) {
    throw new FileUploadError("FILE_TOO_LARGE", "업로드 가능한 파일 크기를 초과했습니다.");
  }

  let response: Response;
  try {
    response = await fetch(grant.upload_url, {
      method: "PUT", body: file, headers: { "Content-Type": contentType },
      credentials: "omit", cache: "no-store", referrerPolicy: "no-referrer", redirect: "error",
      signal: options.signal,
    });
  } catch (error) {
    if (error && typeof error === "object" && "name" in error && error.name === "AbortError") throw error;
    throw new FileUploadError("UPLOAD_NETWORK_ERROR", "파일 업로드 결과를 확인할 수 없습니다.", null, true);
  }
  if (!response.ok) {
    throw new FileUploadError("UPLOAD_FAILED", "파일을 업로드하지 못했습니다.", response.status,
      response.status >= 500);
  }
  return { bucket: grant.bucket, path: grant.path, filename: file.name, size: file.size, content_type: contentType };
}
