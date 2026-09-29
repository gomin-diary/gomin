const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL;

export async function apiFetch(path: string, init?: RequestInit): Promise<Response> {
  if (!apiBaseUrl) throw new Error("NEXT_PUBLIC_API_BASE_URL is not configured");
  if (!path.startsWith("/") || path.startsWith("//")) {
    throw new Error("API paths must start with a single slash");
  }

  const response = await fetch(`${apiBaseUrl.replace(/\/$/, "")}${path}`, {
    ...init,
    cache: "no-store",
  });
  if (!response.ok) throw new Error(`API request failed: ${response.status}`);
  return response;
}
