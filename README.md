# HA Maintenance Agent

A chat-based agent for auditing and maintaining a Home Assistant instance. Ask questions about your entities, devices, and automations, or run maintenance checks to find unused entities, misconfigured automations, and offline devices.

Built with PydanticAI, FastAPI, and React.

## Features

- **Chat interface** with streaming responses and visible tool calls
- **Swappable LLM backend** — select Gemini or any Ollama model from a dropdown
- **Entity tools** — list, search, inspect, and get history for any entity
- **Device tools** — browse devices by manufacturer, area, or keyword
- **Automation tools** — list automations, inspect configs, validate references
- **Area tools** — list areas with entity/device counts, browse area contents
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
│   │   ├── main.py             # FastAPI app, CORS, lifespan
│   │   ├── config.py           # pydantic-settings (.env)
│   │   ├── ha_client.py        # HA REST + WebSocket client
│   │   ├── agent.py            # PydanticAI agent + 17 tools
│   │   ├── models.py           # Pydantic request/response models
│   │   └── routers/
│   │       ├── chat.py         # WebSocket /ws/chat (streaming)
│   │       └── models.py       # GET /api/models
│   └── pyproject.toml
└── frontend/                   # React 19, TypeScript, Vite
    └── src/
        ├── App.tsx             # Layout + model selector
        ├── api/ws.ts           # useAgentChat() WebSocket hook
        └── components/
            ├── Chat.tsx
            ├── ChatInput.tsx
            ├── MessageBubble.tsx
            ├── MessageList.tsx
            └── ModelSelector.tsx
```

## Prerequisites

- Python 3.12+
- Node.js 18+
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- A Home Assistant instance with a long-lived access token
- At least one LLM provider:
  - **Gemini** — requires a Google AI API key
  - **Ollama** — requires a running Ollama instance

## Setup

### 1. Configure environment

Create `src/backend/.env`:

```
HASS_URL=https://your-ha-instance.local:8123
HASS_TOKEN=your_long_lived_access_token
OLLAMA_HOST=http://localhost:11434
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-3-flash-preview
```

### 2. Install dependencies

```bash
# Backend
cd src/backend
uv sync

# Frontend
cd src/frontend
npm install
```

### 3. Run

```bash
# Terminal 1 — backend
cd src/backend
uv run uvicorn app.main:app --reload

# Terminal 2 — frontend
cd src/frontend
npm run dev
```

Open http://localhost:5173. Select a model from the dropdown and start chatting.

## Usage examples

| Prompt | What happens |
|--------|-------------|
| "How many entities do I have?" | Calls `list_entities()` with no filters, returns domain summary |
| "Show me all unavailable lights" | Calls `find_unavailable_entities(domain="light")` |
| "Find unused entities in the switch domain" | Calls `find_unused_entities(domain="switch")`, checks each against automations/scripts/scenes |
| "What automations reference broken entities?" | Calls `validate_automations()`, scans configs for non-existent entity IDs |
| "Show me devices in the kitchen" | Calls `list_devices(area="kitchen")` |
| "What's the history of sensor.living_room_temp?" | Calls `get_entity_history(entity_id="sensor.living_room_temp")` |

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

## How context management works

With 1000+ entities, dumping raw data into the LLM context is impractical. Tools handle this automatically:

- **No filters** — `list_entities()` returns `{total: 2446, summary: {sensor: 938, light: 55, ...}}` instead of 2446 objects
- **With filters** — returns compact tuples `(entity_id, name, state)` with pagination (default 25 per page)
- **Detail tools** — `get_entity_details()` returns full attributes for a single entity
- **Analysis tools** — `find_unused_entities()` cross-references all entities against all automations server-side, only returns the orphans
