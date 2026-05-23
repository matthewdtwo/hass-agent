# HA Maintenance Agent

A chat-based agent for auditing and maintaining a Home Assistant instance. Ask questions about your entities, devices, and automations, or run maintenance checks to find unused entities, misconfigured automations, and offline devices.

Built with PydanticAI, FastAPI, and React.

## Features

- **Chat interface** with streaming responses and expandable tool call details
- **Swappable LLM backend** — select Gemini or any OpenAI-compatible model (llama.cpp, Ollama, etc.) from a dropdown
- **Home Assistant OAuth** — sign in with your existing HA credentials, no separate accounts needed
- **Token usage tracking** — per-session context size, input, and output token counts
- **Entity tools** — list, search, inspect, and get history for any entity
- **Device tools** — browse devices by manufacturer, area, or keyword
- **Automation tools** — list automations, inspect configs, validate references
- **Area tools** — list areas with entity/device counts, browse area contents
- **Dashboard tools** — read and update Lovelace dashboard configurations
- **Maintenance analysis**
  - Find unused entities (not referenced by any automation/script/scene)
  - Find unavailable entities and offline devices
  - Validate automations for broken entity references
  - View the HA error log
- **Context-aware** — tools return summaries for broad queries and paginated details for filtered ones, keeping LLM context usage efficient across 1000+ entities

## Architecture

```
src/
├── backend/                    # Python 3.12+, FastAPI
│   ├── app/
│   │   ├── main.py             # FastAPI app, middleware, lifespan
│   │   ├── config.py           # pydantic-settings (.env)
│   │   ├── auth.py             # Auth helpers, HA user info via WebSocket
│   │   ├── db.py               # SQLite — users, sessions, messages, tokens
│   │   ├── ha_client.py        # HA REST + WebSocket client
│   │   ├── agent.py            # PydanticAI agent + tools
│   │   └── routers/
│   │       ├── auth.py         # HA OAuth flow (login, callback, logout)
│   │       ├── chat.py         # WebSocket /ws/chat (streaming)
│   │       ├── sessions.py     # Session CRUD
│   │       ├── models.py       # GET /api/models
│   │       ├── tokens.py       # Long-lived access token management
│   │       └── config.py       # Runtime config read/write
│   └── pyproject.toml
└── frontend/                   # React 19, TypeScript, Vite
    └── src/
        ├── App.tsx
        ├── api/
        │   ├── ws.ts           # useAgentChat() WebSocket hook
        │   ├── config.ts
        │   └── tokens.ts
        └── components/
            ├── Chat.tsx
            ├── ChatInput.tsx
            ├── MessageBubble.tsx
            ├── ToolCallCard.tsx  # Expandable tool calls with syntax highlighting
            ├── Settings.tsx
            └── ModelSelector.tsx
```

## Prerequisites

- Python 3.12+
- Node.js 18+
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- A Home Assistant instance with a long-lived access token
- At least one LLM provider:
  - **OpenAI-compatible** — any server with an `/v1` API: llama.cpp, Ollama (with `OLLAMA_ORIGINS` set), LM Studio, etc.
  - **Gemini** — requires a Google AI API key

## Setup

### 1. Configure environment

Copy `.env.example` to `.env` and fill in your values:

```bash
cp hass_agent/src/backend/.env.example hass_agent/src/backend/.env
```

Key variables:

| Variable | Description |
|----------|-------------|
| `HASS_URL` | Your HA instance URL, e.g. `http://homeassistant.local:8123` |
| `HASS_TOKEN` | A long-lived access token from your HA profile |
| `OPENAI_BASE_URL` | Base URL of an OpenAI-compatible server, e.g. `http://192.168.1.10:8081` |
| `OPENAI_API_KEY` | API key if required by your server (leave blank for llama.cpp) |
| `GEMINI_API_KEY` | Google AI API key (optional) |
| `OAUTH_REDIRECT_URI` | Where HA redirects after login — must be this app's URL (default: `http://localhost:5173/oauth/callback`) |
| `SESSION_SECRET` | Secret for session cookies — set a fixed value to survive backend restarts |

> **OAuth redirect URI:** This must be the URL of *this app*, not your HA URL. HA sends the user back here after they log in. For local dev the default (`http://localhost:5173/oauth/callback`) works. For LAN/mobile testing use your machine's IP, e.g. `http://192.168.1.x:5173/oauth/callback`.

### 2. Install dependencies

```bash
# Backend
cd hass_agent/src/backend
uv sync

# Frontend
cd hass_agent/src/frontend
npm install
```

### 3. Run

```bash
# Terminal 1 — backend
cd hass_agent/src/backend
uv run uvicorn app.main:app --reload

# Terminal 2 — frontend
cd hass_agent/src/frontend
npm run dev
```

Open http://localhost:5173. You'll be redirected to your Home Assistant instance to log in, then returned to the app.

## Deployment as an HA Add-on

The app ships as a Home Assistant add-on (`config.yaml` at the repo root). When installed via the add-on store it runs with `addon_mode=True`, which automatically authenticates against the Supervisor API — no OAuth redirect configuration needed.

To sideload during development, add the repository URL in **Settings → Add-ons → Add-on store → ⋮ → Repositories**.

## Usage examples

| Prompt | What happens |
|--------|-------------|
| "How many entities do I have?" | Calls `list_entities()` with no filters, returns domain summary |
| "Show me all unavailable lights" | Calls `find_unavailable_entities(domain="light")` |
| "Find unused entities in the switch domain" | Calls `find_unused_entities(domain="switch")`, checks each against automations/scripts/scenes |
| "What automations reference broken entities?" | Calls `validate_automations()`, scans configs for non-existent entity IDs |
| "Show me devices in the kitchen" | Calls `list_devices(area="kitchen")` |
| "What's the history of sensor.living_room_temp?" | Calls `get_entity_history(entity_id="sensor.living_room_temp")` |
| "Update my overview dashboard to add a weather card" | Calls `get_dashboard_config()` then `update_dashboard_config()` |

## Agent tools

| Tool | Description |
|------|-------------|
| `list_entities` | Summary (no filters) or paginated list with domain/area/state/keyword filters |
| `get_entity_details` | Full state, attributes, and registry info for one entity |
| `get_entity_history` | Recent state changes for one entity |
| `search_entities` | Fuzzy search by name or entity ID |
| `list_devices` | Summary (no filters) or filtered list by area/manufacturer/keyword |
| `get_device_details` | Full device info including child entities |
| `list_automations` | Paginated list with keyword/state filters |
| `get_automation_config` | Full YAML config for one automation |
| `list_scripts` | Paginated list with keyword filter |
| `list_areas` | All areas with entity and device counts |
| `get_area_entities` | Entities in a specific area |
| `find_unused_entities` | Entities not in any automation/script/scene (concurrent batched) |
| `find_unavailable_entities` | Entities in unavailable/unknown state |
| `find_offline_devices` | Disabled devices or devices with all entities unavailable |
| `validate_automations` | Automations referencing non-existent entities (concurrent) |
| `get_error_log` | Recent HA error log lines |
| `render_template` | Evaluate a Jinja2 template against HA state |
| `check_config` | Validate HA configuration files |
| `get_dashboard_config` | Read a Lovelace dashboard configuration |
| `update_dashboard_config` | Write/update a Lovelace dashboard configuration |

## API Integration

You can interact with the agent programmatically using long-lived access tokens — useful for connecting other agents, scripts, or automations.

### Creating a token

1. Sign in to the web UI
2. Click **Settings** in the sidebar
3. Enter a name and click **Create**
4. Copy the token immediately — it's only shown once

Tokens look like `haa_<64 hex chars>`.

### Authentication

Include the token as a Bearer token in the `Authorization` header:

```
Authorization: Bearer haa_your_token_here
```

### REST endpoints

**Sessions**

```bash
# List sessions
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/sessions

# Create a session
curl -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title": "My session"}' \
  http://localhost:8000/api/sessions

# Get session with messages
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/sessions/{session_id}

# Delete session
curl -X DELETE -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/sessions/{session_id}
```

**Models**

```bash
# List available models
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/models
```

**Tokens**

```bash
# List your tokens
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/tokens

# Create a new token
curl -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "another-agent"}' \
  http://localhost:8000/api/tokens

# Revoke a token
curl -X DELETE -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/tokens/{token_id}
```

### WebSocket chat

The chat endpoint uses WebSocket at `/ws/chat`. Connect with an optional `session_id` query parameter to resume a conversation:

```
ws://localhost:8000/ws/chat?session_id=optional_session_id
```

> **Note:** WebSocket connections currently authenticate via session cookie only. To use the agent from an external script, use the REST endpoints to manage sessions and send messages through a session-authenticated WebSocket, or extend the WebSocket handler to support Bearer tokens.

### Example: Python client

```python
import httpx

BASE = "http://localhost:8000"
TOKEN = "haa_your_token_here"
HEADERS = {"Authorization": f"Bearer {TOKEN}"}

# Create a session
resp = httpx.post(f"{BASE}/api/sessions", headers=HEADERS, json={"title": "API test"})
session = resp.json()
print(f"Session: {session['id']}")

# List available models
models = httpx.get(f"{BASE}/api/models", headers=HEADERS).json()
print(f"Models: {[m['id'] for m in models]}")
```

## How context management works

With 1000+ entities, dumping raw data into the LLM context is impractical. Tools handle this automatically:

- **No filters** — `list_entities()` returns `{total: 2446, summary: {sensor: 938, light: 55, ...}}` instead of 2446 objects
- **With filters** — returns compact tuples `(entity_id, name, state)` with pagination (default 25 per page)
- **Detail tools** — `get_entity_details()` returns full attributes for a single entity
- **Analysis tools** — `find_unused_entities()` cross-references all entities against all automations server-side, only returns the orphans
