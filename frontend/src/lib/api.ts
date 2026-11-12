export class ApiError extends Error {
  status: number;
  code?: string;
  envVar?: string;
  provider?: string;

  constructor(message: string, status: number, payload?: Record<string, unknown>) {
    super(message);
    this.status = status;
    this.code = payload?.code as string | undefined;
    this.envVar = payload?.env_var as string | undefined;
    this.provider = payload?.provider as string | undefined;
  }
}

const TOKEN_KEY = "nexamind_token";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string | null) {
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

async function parseError(response: Response): Promise<ApiError> {
  let payload: Record<string, unknown> = {};
  try {
    payload = await response.json();
  } catch {
    /* non-JSON error body */
  }
  const detail = typeof payload.detail === "string" ? payload.detail : `Request failed (${response.status})`;
  return new ApiError(detail, response.status, payload);
}

export async function request<T>(
  path: string,
  options: { method?: string; body?: unknown; form?: FormData; token?: string | null } = {}
): Promise<T> {
  const headers: Record<string, string> = {};
  const token = options.token ?? getToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  let body: BodyInit | undefined;
  if (options.form) {
    body = options.form;
  } else if (options.body !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(options.body);
  }
  const response = await fetch(path, { method: options.method ?? "GET", headers, body });
  if (response.status === 401) {
    window.dispatchEvent(new Event("nexamind:unauthorized"));
  }
  if (!response.ok) throw await parseError(response);
  if (response.status === 204) return undefined as T;
  const contentType = response.headers.get("content-type") ?? "";
  if (contentType.includes("application/json")) return (await response.json()) as T;
  return (await response.text()) as unknown as T;
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) => request<T>(path, { method: "POST", body }),
  patch: <T>(path: string, body?: unknown) => request<T>(path, { method: "PATCH", body }),
  del: <T>(path: string) => request<T>(path, { method: "DELETE" }),
  upload: <T>(path: string, form: FormData) => request<T>(path, { method: "POST", form }),
  raw: request
};

export type StreamEvent =
  | { type: "meta"; conversation_id: number; model: string }
  | { type: "delta"; text: string }
  | { type: "done"; message_id: number; model?: string; tokens_in?: number; tokens_out?: number; cost?: number }
  | { type: "error"; error: string };

export async function streamRequest(
  path: string,
  payload: unknown,
  onEvent: (event: StreamEvent) => void,
  signal?: AbortSignal
): Promise<void> {
  const token = getToken();
  const response = await fetch(path, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {})
    },
    body: JSON.stringify(payload),
    signal
  });
  if (!response.ok) throw await parseError(response);
  if (!response.body) throw new ApiError("Streaming is not supported by this browser", 500);
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split("\n\n");
    buffer = parts.pop() ?? "";
    for (const part of parts) {
      const line = part.split("\n").find((l) => l.startsWith("data: "));
      if (!line) continue;
      try {
        onEvent(JSON.parse(line.slice(6)) as StreamEvent);
      } catch {
        /* ignore malformed keepalive */
      }
    }
  }
}

export async function streamChat(
  payload: Record<string, unknown>,
  onEvent: (event: StreamEvent) => void,
  signal?: AbortSignal
): Promise<void> {
  return streamRequest("/api/chat/stream", payload, onEvent, signal);
}

export function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

export async function downloadMedia(id: number, filename: string) {
  const token = getToken();
  const response = await fetch(`/api/media/${id}/file`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {}
  });
  if (!response.ok) throw await parseError(response);
  downloadBlob(await response.blob(), filename);
}
