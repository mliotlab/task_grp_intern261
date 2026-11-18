/**
 * Thin typed wrapper around fetch. Types should mirror docs/api/openapi.yaml.
 * TODO(Sprint 2): generate types from the OpenAPI spec (e.g. `openapi-typescript`) instead of
 * maintaining them by hand.
 */
export const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

const TOKEN_KEY = "era.token";

export const auth = {
  get token(): string | null {
    return localStorage.getItem(TOKEN_KEY);
  },
  set token(value: string | null) {
    if (value) localStorage.setItem(TOKEN_KEY, value);
    else localStorage.removeItem(TOKEN_KEY);
  },
};

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (auth.token) headers.set("Authorization", `Bearer ${auth.token}`);
  if (init.body && !(init.body instanceof FormData)) headers.set("Content-Type", "application/json");

  const res = await fetch(`${API_URL}${path}`, { ...init, headers });
  if (res.status === 401) auth.token = null;
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new ApiError(res.status, body.detail ?? res.statusText);
  }
  return (res.status === 204 ? undefined : await res.json()) as T;
}

export type JobStatus = "queued" | "running" | "succeeded" | "failed" | "cancelled";

export interface ResearchJob {
  job_id: string;
  question: string;
  status: JobStatus;
  steps: { name: string; status: string; duration_ms?: number | null }[];
  report_markdown?: string | null;
  error?: string | null;
}
