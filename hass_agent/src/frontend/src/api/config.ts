export interface AddonConfig {
  /** Masked as "***" when set; send the real value to update. */
  gemini_api_key: string;
  gemini_model: string;
  preferred_model: string;
  addon_mode: boolean;
}

export async function getConfig(): Promise<AddonConfig> {
  const resp = await fetch("api/config");
  if (!resp.ok) throw new Error("Failed to get config");
  return resp.json();
}

export interface ConfigUpdate {
  gemini_api_key?: string;
  gemini_model?: string;
  preferred_model?: string;
}

export async function updateConfig(data: ConfigUpdate): Promise<void> {
  const resp = await fetch("api/config", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!resp.ok) throw new Error("Failed to update config");
}
