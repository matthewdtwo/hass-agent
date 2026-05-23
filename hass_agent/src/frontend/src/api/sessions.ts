import type { DisplayMessage, SessionInfo, TokenUsage } from "../types";

const BASE = "api/sessions";

export interface SessionDetailResult {
  messages: DisplayMessage[];
  token_usage: TokenUsage | null;
}

export async function listSessions(): Promise<SessionInfo[]> {
  const resp = await fetch(BASE);
  return resp.json();
}

export async function createSession(title?: string): Promise<SessionInfo> {
  const resp = await fetch(BASE, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(title ? { title } : {}),
  });
  return resp.json();
}

export async function getSessionMessages(
  id: string
): Promise<DisplayMessage[]> {
  const resp = await fetch(`${BASE}/${id}`);
  const data = await resp.json();
  return data.messages;
}

export async function getSessionDetail(
  id: string
): Promise<SessionDetailResult> {
  const resp = await fetch(`${BASE}/${id}`);
  const data = await resp.json();
  return {
    messages: data.messages,
    token_usage: data.token_usage ?? null,
  };
}

export async function deleteSession(id: string): Promise<void> {
  await fetch(`${BASE}/${id}`, { method: "DELETE" });
}

export async function updateSessionTitle(
  id: string,
  title: string
): Promise<void> {
  await fetch(`${BASE}/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title }),
  });
}
