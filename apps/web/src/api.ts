/** Typed API client. Token lives in localStorage; every request is circle-scoped
 * on the server via Membership checks. */
const BASE = "/api";

export function getToken(): string | null {
  return localStorage.getItem("ihtama_token");
}
export function setToken(t: string | null) {
  if (t) localStorage.setItem("ihtama_token", t);
  else localStorage.removeItem("ihtama_token");
}

async function req<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = { ...(options.headers as any) };
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  if (options.body && typeof options.body === "string") headers["Content-Type"] = "application/json";
  const r = await fetch(`${BASE}${path}`, { ...options, headers });
  if (r.status === 401) {
    setToken(null);
    window.location.href = "/login";
    throw new Error("Session expired");
  }
  if (!r.ok) {
    const body = await r.json().catch(() => ({}));
    const detail = body.detail;
    const message = Array.isArray(detail)
      ? detail.map((d: any) => d.msg || JSON.stringify(d)).join("; ")
      : (typeof detail === "string" ? detail : detail ? JSON.stringify(detail) : `Request failed (${r.status})`);
    throw new Error(message);
  }
  return r.json();
}

// ---- types ----
export type Member = { user_id: string; name: string; email: string; role: string };
export type Circle = {
  id: string; recipient_name: string; recipient_dob: string; recipient_notes: string;
  invite_code: string; consent_recorded_at: string | null; members: Member[]; my_role?: string;
};
export type ExtractedItem = {
  id: string; kind: string; payload: Record<string, any>; source_page: number;
  source_quote: string; confidence: number; flags: string[]; review_status: string;
};
export type Doc = {
  id: string; filename: string; doc_type: string; status: string; summary: string;
  reject_reason: string; created_at: string; items?: ExtractedItem[];
  review_request?: { validation_issues: string[] } | null;
};
export type CareUpdate = {
  id: string; author: string | null; transcript: string; structured: Record<string, any>;
  red_flags: string[]; status: string; created_at: string;
  confirm_request?: Record<string, any> | null;
};
export type Citation = { doc_id: string; doc_name: string; page: number; quote: string };
export type ChatMsg = { id: string; role: string; content: string; citations: Citation[]; route: string; created_at: string };
export type Plan = {
  medications: { id: string; name: string; dose: string; schedule: string }[];
  appointments: { id: string; when: string; where: string; what: string; status: string }[];
  tasks: { id: string; title: string; due: string; status: string; source: string }[];
};
export type Today = {
  recipient_name: string;
  approvals_waiting: Doc[];
  latest_update: { id: string; structured: Record<string, any>; at: string } | null;
  next_appointment: { when: string; what: string; where: string } | null;
  open_tasks: number; medications_count: number;
  medications: { name: string; dose: string; schedule: string }[];
  alerts: string[];
};

// ---- calls ----
export const api = {
  login: (email: string, password: string) =>
    req<{ token: string; user: any }>("/auth/login", { method: "POST", body: JSON.stringify({ email, password }) }),
  register: (email: string, name: string, password: string) =>
    req<{ token: string; user: any }>("/auth/register", { method: "POST", body: JSON.stringify({ email, name, password }) }),
  me: () => req<any>("/auth/me"),
  circles: () => req<Circle[]>("/circles"),
  createCircle: (data: any) => req<Circle>("/circles", { method: "POST", body: JSON.stringify(data) }),
  joinCircle: (invite_code: string, role: string) =>
    req<Circle>("/circles/join", { method: "POST", body: JSON.stringify({ invite_code, role }) }),
  circle: (id: string) => req<Circle>(`/circles/${id}`),
  audit: (id: string) => req<any[]>(`/circles/${id}/audit`),
  today: (id: string) => req<Today>(`/circles/${id}/today`),
  plan: (id: string) => req<Plan>(`/circles/${id}/plan`),
  toggleTask: (taskId: string) => req(`/tasks/${taskId}/toggle`, { method: "POST" }),
  addTask: (circleId: string, title: string, due = "") =>
    req(`/circles/${circleId}/tasks`, { method: "POST", body: JSON.stringify({ title, due }) }),
  documents: (id: string) => req<Doc[]>(`/circles/${id}/documents`),
  document: (docId: string) => req<Doc>(`/documents/${docId}`),
  uploadDocument: (circleId: string, file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return req<{ id: string; status: string }>(`/circles/${circleId}/documents`, { method: "POST", body: fd });
  },
  review: (docId: string, body: { action: string; items?: Record<string, string>; edits?: Record<string, any>; reason?: string }) =>
    req<Doc>(`/documents/${docId}/review`, { method: "POST", body: JSON.stringify(body) }),
  updates: (id: string) => req<CareUpdate[]>(`/circles/${id}/updates`),
  createUpdate: (circleId: string, audio: Blob | null, filename: string, text = "") => {
    const fd = new FormData();
    if (audio) fd.append("audio", audio, filename);
    fd.append("text", text);
    return req<CareUpdate>(`/circles/${circleId}/updates`, { method: "POST", body: fd });
  },
  confirmUpdate: (updateId: string, action: "confirmed" | "discarded", structured?: any) =>
    req<CareUpdate>(`/updates/${updateId}/confirm`, { method: "POST", body: JSON.stringify({ action, structured }) }),
  ask: (circleId: string, question: string, variant = "A") =>
    req<{ id: string; answer: string; citations: Citation[]; route: string }>(
      `/circles/${circleId}/ask`, { method: "POST", body: JSON.stringify({ question, variant }) }),
  messages: (circleId: string) => req<ChatMsg[]>(`/circles/${circleId}/messages`),
  health: () => req<{ demo_mode: boolean }>("/health"),
};
