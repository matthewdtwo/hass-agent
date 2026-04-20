export interface User {
  id: string;
  email: string;
  name: string;
  picture?: string;
  ha_user_id?: string;
  is_admin?: boolean;
}

export async function checkAuth(): Promise<User | null> {
  const resp = await fetch("api/auth/check");
  if (!resp.ok) return null;
  return resp.json();
}

export function loginUrl(): string {
  return "api/auth/login";
}

export async function logout(): Promise<void> {
  await fetch("api/auth/logout", { method: "POST" });
}
