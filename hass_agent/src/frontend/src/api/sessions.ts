import type { DisplayMessage, SessionInfo } from "../types";

const BASE = "api/sessions";

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
