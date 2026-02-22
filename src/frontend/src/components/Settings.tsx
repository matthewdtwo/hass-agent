import { useCallback, useEffect, useState } from "react";
import { getConfig, updateConfig, type AddonConfig } from "../api/config";
import {
  createToken,
  deleteToken,
  listTokens,
  type CreateTokenResponse,
  type TokenInfo,
} from "../api/tokens";

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

function Field({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <label className="block text-sm font-medium text-gray-300">{label}</label>
      {hint && <p className="mt-0.5 text-xs text-gray-500">{hint}</p>}
      <div className="mt-1.5">{children}</div>
    </div>
  );
}

// ── Configuration section ────────────────────────────────────────────────────

function ConfigSection() {
  const [config, setConfig] = useState<AddonConfig | null>(null);
  const [ollamaHost, setOllamaHost] = useState("");
  const [geminiKey, setGeminiKey] = useState("");
  const [geminiModel, setGeminiModel] = useState("");
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getConfig()
      .then((c) => {
        setConfig(c);
        setOllamaHost(c.ollama_host);
        setGeminiKey(c.gemini_api_key); // will be "***" or ""
        setGeminiModel(c.gemini_model);
      })
      .catch(() => setError("Could not load configuration."));
  }, []);

  const handleSave = useCallback(async () => {
    setSaving(true);
    setError(null);
    try {
      await updateConfig({
        ollama_host: ollamaHost,
        // Only send the key if the user typed a new one (not the masked placeholder)
        ...(geminiKey !== "***" ? { gemini_api_key: geminiKey } : {}),
        gemini_model: geminiModel,
      });
      setSaved(true);
      setTimeout(() => setSaved(false), 2500);
    } catch {
      setError("Failed to save configuration.");
    } finally {
      setSaving(false);
    }
  }, [ollamaHost, geminiKey, geminiModel]);

  if (!config) {
    return <p className="text-sm text-gray-500">Loading…</p>;
  }

  return (
    <section>
      <h2 className="text-xl font-semibold text-gray-100">Configuration</h2>
      <p className="mt-1 text-sm text-gray-400">
        AI provider settings. Changes take effect immediately without a restart.
        {config.addon_mode && (
          <span className="ml-1 text-gray-500">
            (also written to <code>/data/options.json</code>)
          </span>
        )}
      </p>

      <div className="mt-6 space-y-5">
        <Field
          label="Ollama host"
          hint="Full URL of your Ollama instance, e.g. http://192.168.1.10:11434"
        >
          <input
            value={ollamaHost}
            onChange={(e) => setOllamaHost(e.target.value)}
            type="url"
            placeholder="http://host:11434"
            className="w-full rounded-lg border border-gray-700 bg-gray-900 px-3 py-2 text-sm text-gray-100 placeholder-gray-600 focus:border-gray-500 focus:outline-none"
          />
        </Field>

        <Field
          label="Gemini API key"
          hint="Google AI Studio key. Leave blank to keep the existing key."
        >
          <input
            value={geminiKey}
            onChange={(e) => setGeminiKey(e.target.value)}
            type="password"
            placeholder={config.gemini_api_key ? "••••••••" : "Paste key here"}
            autoComplete="off"
            className="w-full rounded-lg border border-gray-700 bg-gray-900 px-3 py-2 text-sm text-gray-100 placeholder-gray-600 focus:border-gray-500 focus:outline-none"
          />
        </Field>

        <Field label="Gemini model" hint="Model ID passed to the Google AI API.">
          <input
            value={geminiModel}
            onChange={(e) => setGeminiModel(e.target.value)}
            placeholder="gemini-2.0-flash"
            className="w-full rounded-lg border border-gray-700 bg-gray-900 px-3 py-2 text-sm text-gray-100 placeholder-gray-600 focus:border-gray-500 focus:outline-none"
          />
        </Field>
      </div>

      {error && <p className="mt-4 text-sm text-red-400">{error}</p>}

      <div className="mt-6 flex items-center gap-4">
        <button
          onClick={handleSave}
          disabled={saving}
          className="rounded-lg bg-gray-100 px-5 py-2 text-sm font-medium text-gray-900 transition-colors hover:bg-gray-300 disabled:cursor-not-allowed disabled:opacity-40"
        >
          {saving ? "Saving…" : "Save"}
        </button>
        {saved && (
          <span className="text-sm text-green-400">Saved successfully.</span>
        )}
      </div>
    </section>
  );
}

// ── Access tokens section ────────────────────────────────────────────────────

function TokensSection() {
  const [tokens, setTokens] = useState<TokenInfo[]>([]);
  const [name, setName] = useState("");
  const [newToken, setNewToken] = useState<CreateTokenResponse | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    listTokens().then(setTokens).catch(() => {});
  }, []);

  const handleCreate = useCallback(async () => {
    const trimmed = name.trim();
    if (!trimmed) return;
    const resp = await createToken(trimmed);
    setNewToken(resp);
    setTokens((prev) => [resp, ...prev]);
    setName("");
  }, [name]);

  const handleDelete = useCallback(async (id: string) => {
    await deleteToken(id);
    setTokens((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const handleCopy = useCallback(() => {
    if (!newToken) return;
    navigator.clipboard.writeText(newToken.token);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }, [newToken]);

  return (
    <section>
      <h2 className="text-xl font-semibold text-gray-100">Access Tokens</h2>
      <p className="mt-1 text-sm text-gray-400">
        Create long-lived tokens to access the API from external agents.
      </p>

      {/* Create form */}
      <div className="mt-6 flex gap-3">
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleCreate()}
          placeholder="Token name (e.g. my-agent)"
          className="flex-1 rounded-lg border border-gray-700 bg-gray-900 px-3 py-2 text-sm text-gray-100 placeholder-gray-600 focus:border-gray-500 focus:outline-none"
        />
        <button
          onClick={handleCreate}
          disabled={!name.trim()}
          className="rounded-lg bg-gray-100 px-4 py-2 text-sm font-medium text-gray-900 transition-colors hover:bg-gray-300 disabled:cursor-not-allowed disabled:opacity-40"
        >
          Create
        </button>
      </div>

      {/* Newly created token banner */}
      {newToken && (
        <div className="mt-4 rounded-lg border border-yellow-800 bg-yellow-950/50 p-4">
          <p className="text-sm font-medium text-yellow-200">
            Copy your token now — it won't be shown again.
          </p>
          <div className="mt-2 flex items-center gap-2">
            <code className="flex-1 overflow-x-auto rounded bg-gray-900 px-3 py-2 text-sm text-gray-100">
              {newToken.token}
            </code>
            <button
              onClick={handleCopy}
              className="shrink-0 rounded-lg border border-gray-700 px-3 py-2 text-sm text-gray-300 transition-colors hover:bg-gray-800"
            >
              {copied ? "Copied!" : "Copy"}
            </button>
          </div>
          <button
            onClick={() => setNewToken(null)}
            className="mt-2 text-xs text-gray-500 hover:text-gray-400"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Token list */}
      <div className="mt-6">
        {tokens.length === 0 ? (
          <p className="text-sm text-gray-600">No tokens created yet.</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-800 text-left text-gray-500">
                <th className="pb-2 font-medium">Name</th>
                <th className="pb-2 font-medium">Created</th>
                <th className="pb-2 font-medium">Last used</th>
                <th className="pb-2" />
              </tr>
            </thead>
            <tbody>
              {tokens.map((t) => (
                <tr
                  key={t.id}
                  className="border-b border-gray-800/50 text-gray-300"
                >
                  <td className="py-2.5">{t.name}</td>
                  <td className="py-2.5 text-gray-500">{timeAgo(t.created_at)}</td>
                  <td className="py-2.5 text-gray-500">
                    {t.last_used ? timeAgo(t.last_used) : "Never"}
                  </td>
                  <td className="py-2.5 text-right">
                    <button
                      onClick={() => handleDelete(t.id)}
                      className="rounded px-2 py-1 text-gray-600 transition-colors hover:bg-gray-800 hover:text-red-400"
                    >
                      Revoke
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </section>
  );
}

// ── Page ─────────────────────────────────────────────────────────────────────

export default function Settings() {
  return (
    <div className="mx-auto max-w-2xl space-y-12 px-6 py-8">
      <ConfigSection />
      <hr className="border-gray-800" />
      <TokensSection />
    </div>
  );
}
