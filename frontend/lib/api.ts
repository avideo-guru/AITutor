// Typed API client + SSE consumer. expo/fetch gives streaming bodies on
// native and web alike.

import { fetch as streamingFetch } from "expo/fetch";

import { accessToken, supabase } from "@/lib/auth";

const API_URL = process.env.EXPO_PUBLIC_API_URL ?? "http://localhost:8080";

export type Me = {
  id: string;
  email: string;
  exam_target: string;
  plan: "free" | "pro";
  plan_expires_at: string | null;
  questions_remaining_today: number | null; // null = unlimited (pro)
  free_daily_limit: number;
};

export type SessionItem = {
  id: string;
  thread_id: string | null;
  question: string;
  image_url: string | null;
  answer: string | null;
  model: string | null;
  feedback_rating: "up" | "down" | null;
  created_at: string;
};

export class ApiError extends Error {
  constructor(public status: number, public code: string, message: string) {
    super(message);
  }
}

async function authHeaders(): Promise<Record<string, string>> {
  const token = await accessToken();
  return {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

async function toApiError(res: Response | { status: number; json(): Promise<unknown> }) {
  let code = "UNKNOWN";
  let message = "Request failed";
  try {
    const body = (await res.json()) as { error?: { code: string; message: string } };
    if (body.error) ({ code, message } = body.error);
  } catch { /* non-JSON error body */ }
  return new ApiError(res.status, code, message);
}

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: { ...(await authHeaders()), ...(init?.headers as object) },
  });
  if (!res.ok) throw await toApiError(res);
  return res.status === 204 ? (undefined as T) : ((await res.json()) as T);
}

// ---------------------------------------------------------------- ask (SSE)

export type AskMeta = {
  session_id: string;
  thread_id: string;
  model: string | null;
  sources: string[];
};

export type AskCallbacks = {
  onToken: (t: string) => void;
  onMeta: (m: AskMeta) => void;
  onError: (code: string, message: string) => void;
  onDone: () => void;
};

export async function askStream(
  body: { text?: string; image_url?: string; chapter?: string; thread_id?: string },
  cb: AskCallbacks,
): Promise<void> {
  const res = await streamingFetch(`${API_URL}/v1/ask`, {
    method: "POST",
    headers: await authHeaders(),
    body: JSON.stringify(body),
  });
  if (!res.ok || !res.body) {
    const err = await toApiError(res);
    cb.onError(err.code, err.message);
    return;
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buf = "";

  const handle = (block: string) => {
    let event = "message";
    let data = "";
    for (const line of block.split("\n")) {
      if (line.startsWith("event:")) event = line.slice(6).trim();
      else if (line.startsWith("data:")) data += line.slice(5).trim();
    }
    if (!data) return;
    const payload = JSON.parse(data);
    if (event === "token") cb.onToken(payload.t);
    else if (event === "meta") cb.onMeta(payload);
    else if (event === "error") cb.onError(payload.code, payload.message);
    else if (event === "done") cb.onDone();
  };

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    let idx;
    while ((idx = buf.indexOf("\n\n")) >= 0) {
      const block = buf.slice(0, idx);
      buf = buf.slice(idx + 2);
      if (block.trim()) handle(block);
    }
  }
}

// ----------------------------------------------------------- sessions

export function getSession(id: string): Promise<SessionItem> {
  return api<SessionItem>(`/v1/sessions/${id}`);
}

export function sendFeedback(
  sessionId: string,
  rating: "up" | "down",
  reason?: string,
): Promise<void> {
  return api<void>(`/v1/sessions/${sessionId}/feedback`, {
    method: "POST",
    body: JSON.stringify({ rating, ...(reason ? { reason } : {}) }),
  });
}

// ------------------------------------------------------------ image upload

export async function uploadQuestionImage(
  base64: string,
  mimeType: string,
): Promise<string> {
  const bytes = Uint8Array.from(atob(base64), (c) => c.charCodeAt(0));
  const ext = mimeType.split("/")[1] ?? "jpg";
  const path = `${crypto.randomUUID()}.${ext}`;
  const { error } = await supabase.storage
    .from("question-images")
    .upload(path, bytes.buffer as ArrayBuffer, { contentType: mimeType });
  if (error) throw new Error(`Image upload failed: ${error.message}`);
  return supabase.storage.from("question-images").getPublicUrl(path).data.publicUrl;
}
