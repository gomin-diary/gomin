import { apiFetch } from "./api";
import type { SummaryHandoff, TalkApi, TalkConversation, TalkJob, TalkMessage } from "./talk";

const path = (id: string) => `/api/v1/conversations/${encodeURIComponent(id)}`;
const post = (body?: unknown): RequestInit => ({ method: "POST", headers: { "Content-Type": "application/json" }, ...(body ? { body: JSON.stringify(body) } : {}) });
export const talkApi: TalkApi = {
  create: () => apiFetch<TalkConversation>("/api/v1/conversations", post()),
  read: (id) => apiFetch<TalkConversation>(path(id)),
  send: (id, content, client_message_id) => apiFetch<{ message: TalkMessage; job: TalkJob }>(`${path(id)}/messages`, post({ content, client_message_id })),
  summarize: (id, request_id) => apiFetch<TalkJob>(`${path(id)}/summaries`, post({ request_id })),
  resume: (id) => apiFetch<TalkConversation>(`${path(id)}/resume`, post()),
  confirm: (id, summaryId) => apiFetch<SummaryHandoff>(`${path(id)}/summaries/${encodeURIComponent(summaryId)}/confirm`, post()),
  handoff: (id, summaryId) => apiFetch<SummaryHandoff>(`${path(id)}/summaries/${encodeURIComponent(summaryId)}/handoff`),
};
