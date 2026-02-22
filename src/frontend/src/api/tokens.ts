export interface TokenInfo {
  id: string;
  name: string;
  created_at: string;
  last_used: string | null;
}

export interface CreateTokenResponse extends TokenInfo {
  token: string;
}

export async function listTokens(): Promise<TokenInfo[]> {
  const resp = await fetch("api/tokens");
  if (!resp.ok) throw new Error("Failed to list tokens");
  return resp.json();
}

export async function createToken(name: string): Promise<CreateTokenResponse> {
  const resp = await fetch("api/tokens", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  });
  if (!resp.ok) throw new Error("Failed to create token");
  return resp.json();
}

export async function deleteToken(id: string): Promise<void> {
  const resp = await fetch(`api/tokens/${id}`, { method: "DELETE" });
  if (!resp.ok) throw new Error("Failed to delete token");
}
