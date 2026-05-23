import { useCallback, useEffect, useState } from "react";
import { getConfig, updateConfig, type AddonConfig } from "../api/config";
import type { ModelInfo } from "../types";
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
      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">{label}</label>
      {hint && <p className="mt-0.5 text-xs text-gray-500 dark:text-gray-400">{hint}</p>}
      <div className="mt-1.5">{children}</div>
    </div>
  );
}

const inputClass =
  "w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-900 placeholder-gray-400 focus:border-gray-400 focus:outline-none dark:border-gray-700 dark:bg-gray-900 dark:text-gray-100 dark:placeholder-gray-600 dark:focus:border-gray-500";

const btnPrimaryClass =
  "rounded-lg bg-gray-800 px-5 py-2 text-sm font-medium text-white transition-colors hover:bg-gray-700 disabled:cursor-not-allowed disabled:opacity-40 dark:bg-gray-100 dark:text-gray-900 dark:hover:bg-gray-300";

// ── Configuration section ────────────────────────────────────────────────────

function ConfigSection({ onPreferredModelChange }: { onPreferredModelChange?: (model: string) => void }) {
  const [config, setConfig] = useState<AddonConfig | null>(null);
  const [geminiKey, setGeminiKey] = useState("");
  const [geminiModel, setGeminiModel] = useState("");
  const [preferredModel, setPreferredModel] = useState("");
  const [maxContextTokens, setMaxContextTokens] = useState(16384);
  const [availableModels, setAvailableModels] = useState<ModelInfo[]>([]);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      getConfig(),
      fetch("api/models").then((r) => (r.ok ? r.json() : [])).catch(() => []),
    ])
      .then(([c, models]) => {
        setConfig(c);
        setGeminiKey(c.gemini_api_key); // will be "***" or ""
        setGeminiModel(c.gemini_model);
        setPreferredModel(c.preferred_model);
        setMaxContextTokens(c.max_context_tokens ?? 16384);
        setAvailableModels(models);
      })
      .catch(() => setError("Could not load configuration."));
  }, []);

  const handleSave = useCallback(async () => {
    setSaving(true);
    setError(null);
    try {
      await updateConfig({
        // Only send the key if the user typed a new one (not the masked placeholder)
        ...(geminiKey !== "***" ? { gemini_api_key: geminiKey } : {}),
        gemini_model: geminiModel,
        preferred_model: preferredModel,
        max_context_tokens: maxContextTokens,
      });
      setSaved(true);
      onPreferredModelChange?.(preferredModel);
      setTimeout(() => setSaved(false), 2500);
    } catch {
      setError("Failed to save configuration.");
    } finally {
      setSaving(false);
    }
  }, [geminiKey, geminiModel, preferredModel, maxContextTokens]);

  if (!config) {
    return <p className="text-sm text-gray-500">Loading…</p>;
  }

  return (
    <section>
      <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">Configuration</h2>
      <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
        AI provider settings. Changes take effect immediately without a restart.
        {config.addon_mode && (
          <span className="ml-1 text-gray-400 dark:text-gray-500">
            (also written to <code>/data/options.json</code>)
          </span>
        )}
      </p>

      <div className="mt-6 space-y-5">
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
            className={inputClass}
          />
        </Field>

        <Field label="Gemini model" hint="Model ID passed to the Google AI API.">
          <input
            value={geminiModel}
            onChange={(e) => setGeminiModel(e.target.value)}
            placeholder="gemini-3.1-flash-lite"
            className={inputClass}
          />
        </Field>

        <Field
          label="Preferred model"
          hint="Model selected by default when the app loads. Leave blank to auto-select the first available."
        >
          <select
            value={preferredModel}
            onChange={(e) => setPreferredModel(e.target.value)}
            className={inputClass}
          >
            <option value="">(auto — first available)</option>
            {availableModels.map((m) => (
              <option key={m.id} value={m.id}>
                {m.provider.toUpperCase()} — {m.name}
              </option>
            ))}
          </select>
        </Field>

        <Field
          label="Max context tokens"
          hint="Sliding window limit. When exceeded, older messages are summarized automatically. Default: 16384."
        >
          <input
            type="number"
            min={1024}
            step={1024}
            value={maxContextTokens}
            onChange={(e) => setMaxContextTokens(Number(e.target.value))}
            className={inputClass}
          />
        </Field>
      </div>

      {error && <p className="mt-4 text-sm text-red-500 dark:text-red-400">{error}</p>}

      <div className="mt-6 flex items-center gap-4">
        <button
          onClick={handleSave}
          disabled={saving}
          className={btnPrimaryClass}
        >
          {saving ? "Saving…" : "Save"}
        </button>
        {saved && (
          <span className="text-sm text-green-600 dark:text-green-400">Saved successfully.</span>
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
      <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">Access Tokens</h2>
      <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
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
          className={inputClass}
        />
        <button
          onClick={handleCreate}
          disabled={!name.trim()}
          className={btnPrimaryClass}
        >
          Create
        </button>
      </div>

      {/* Newly created token banner */}
      {newToken && (
        <div className="mt-4 rounded-lg border border-yellow-300 bg-yellow-50 p-4 dark:border-yellow-800 dark:bg-yellow-950/50">
          <p className="text-sm font-medium text-yellow-800 dark:text-yellow-200">
            Copy your token now — it won't be shown again.
          </p>
          <div className="mt-2 flex items-center gap-2">
            <code className="flex-1 overflow-x-auto rounded bg-white px-3 py-2 text-sm text-gray-900 dark:bg-gray-900 dark:text-gray-100">
              {newToken.token}
            </code>
            <button
              onClick={handleCopy}
              className="shrink-0 rounded-lg border border-gray-200 px-3 py-2 text-sm text-gray-700 transition-colors hover:bg-gray-100 dark:border-gray-700 dark:text-gray-300 dark:hover:bg-gray-800"
            >
              {copied ? "Copied!" : "Copy"}
            </button>
          </div>
          <button
            onClick={() => setNewToken(null)}
            className="mt-2 text-xs text-gray-400 hover:text-gray-600 dark:text-gray-500 dark:hover:text-gray-400"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Token list */}
      <div className="mt-6">
        {tokens.length === 0 ? (
          <p className="text-sm text-gray-500 dark:text-gray-600">No tokens created yet.</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 text-left text-gray-500 dark:border-gray-800 dark:text-gray-500">
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
                  className="border-b border-gray-100 text-gray-700 dark:border-gray-800/50 dark:text-gray-300"
                >
                  <td className="py-2.5">{t.name}</td>
                  <td className="py-2.5 text-gray-400 dark:text-gray-500">{timeAgo(t.created_at)}</td>
                  <td className="py-2.5 text-gray-400 dark:text-gray-500">
                    {t.last_used ? timeAgo(t.last_used) : "Never"}
                  </td>
                  <td className="py-2.5 text-right">
                    <button
                      onClick={() => handleDelete(t.id)}
                      className="rounded px-2 py-1 text-gray-400 transition-colors hover:bg-gray-100 hover:text-red-500 dark:text-gray-600 dark:hover:bg-gray-800 dark:hover:text-red-400"
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

export default function Settings({ onPreferredModelChange }: { onPreferredModelChange?: (model: string) => void }) {
  return (
    <div className="mx-auto max-w-2xl space-y-12 overflow-y-auto px-6 py-8">
      <ConfigSection onPreferredModelChange={onPreferredModelChange} />
      <hr className="border-gray-200 dark:border-gray-800" />
      <TokensSection />
    </div>
  );
}
