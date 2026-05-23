# HA Agent — Project Guidelines

## Addon Version

**Always bump `hass_agent/config.yaml` version when making user-visible changes.**

- Patch (`x.y.Z`): bug fixes, minor tweaks
- Minor (`x.Y.0`): new features, non-breaking changes
- Major (`X.0.0`): breaking changes, removed features, auth changes

The version field is on line 2: `version: "X.Y.Z"`

## Architecture

```
hass_agent/
├── config.yaml               # HA addon manifest — version lives here
└── src/
    ├── backend/              # Python 3.12+, FastAPI, PydanticAI
    │   ├── app/
    │   │   ├── config.py     # pydantic-settings; reads .env + /data/options.json (addon mode)
    │   │   ├── agent.py      # PydanticAI agent + all HA tools
    │   │   ├── ha_client.py  # HA REST + WebSocket client
    │   │   ├── db.py         # SQLite: users, sessions, messages, access tokens
    │   │   ├── auth.py       # HA OAuth helpers
    │   │   └── routers/
    │   │       ├── auth.py   # HA OAuth flow (login → HA → callback → session)
    │   │       ├── chat.py   # WebSocket /ws/chat — streaming, tool calls, token tracking
    │   │       ├── config.py # Runtime config API (gemini key, model, preferred model)
    │   │       ├── models.py # Model discovery: Gemini + OpenAI-compatible servers
    │   │       ├── sessions.py
    │   │       └── tokens.py # Long-lived bearer tokens
    │   └── .env              # Local secrets — never commit (gitignored)
    └── frontend/             # React 19, TypeScript, Vite, Tailwind
        └── src/
            ├── api/          # fetch wrappers + useAgentChat() WS hook
            └── components/   # Chat, ToolCallCard, Settings, ModelSelector
```

## Key Conventions

- **LLM providers**: OpenAI-compatible (`openai:` prefix, `OPENAI_BASE_URL`) and Gemini (`google-gla:` prefix). No Ollama-specific code — Ollama works via the OpenAI-compatible endpoint.
- **Auth**: HA OAuth only. No Google OAuth. `oauth_state` is stored in a dedicated cookie (not session) to survive Vite proxy redirects.
- **Addon mode**: `ADDON_MODE=true` skips OAuth; the Supervisor injects auth. Settings overlay from `/data/options.json`.
- **Tool results**: Use `_to_json_str()` in `chat.py` to serialize HA tool outputs — handles Python repr dicts via `ast.literal_eval`.
- **`.env` never committed**: Real secrets stay in `hass_agent/src/backend/.env` (gitignored). Document new env vars in `.env.example`.

## Build & Run

```bash
# Backend
cd hass_agent/src/backend && uv run uvicorn app.main:app --reload

# Frontend
cd hass_agent/src/frontend && npm run dev
```

Frontend proxies `/api` and `/oauth` to `http://localhost:8000` via Vite.
