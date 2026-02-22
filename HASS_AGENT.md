# HA Agent Integration Guide

You are integrating with HA Agent — a Home Assistant maintenance assistant with a chat-based API. It can query entities, devices, automations, services, and system health, and perform maintenance actions like creating automations or removing stale entities.

## Base URL

```
http://localhost:8000
```

## Authentication

All requests require a Bearer token in the `Authorization` header:

```
Authorization: Bearer haa_<token>
```

Tokens are long-lived and do not expire. Include this header on every HTTP request.

## API Reference

### Models

```
GET /api/models
```

Returns the list of available LLM backends. Use the `id` field when sending chat messages.

Response:
```json
[
  {"id": "google-gla:gemini-3-flash-preview", "provider": "gemini", "name": "gemini-3-flash-preview"},
  {"id": "ollama:llama3:latest", "provider": "ollama", "name": "llama3:latest"}
]
```

### Sessions

Sessions are conversations. Each session maintains its own message history and LLM context.

```
POST /api/sessions
```
Body: `{"title": "descriptive session name"}`
Returns: `{"id": "<session_id>", "title": "...", "created_at": "...", "updated_at": "..."}`

```
GET /api/sessions
```
Returns all your sessions, newest first.

```
GET /api/sessions/{session_id}
```
Returns the session with its full message history.

Response:
```json
{
  "id": "abc123",
  "title": "Check kitchen sensors",
  "created_at": "2026-02-16T...",
  "updated_at": "2026-02-16T...",
  "messages": [
    {"id": 1, "role": "user", "content": "...", "tool_calls": null, "created_at": "..."},
    {"id": 2, "role": "assistant", "content": "...", "tool_calls": [...], "created_at": "..."}
  ]
}
```

```
DELETE /api/sessions/{session_id}
```
Deletes a session and all its messages.

### Chat (WebSocket)

The chat endpoint is a WebSocket connection. This is the primary way to interact with the agent.

```
ws://localhost:8000/ws/chat
ws://localhost:8000/ws/chat?session_id=<session_id>
```

> **Important:** WebSocket auth currently uses session cookies, not Bearer tokens. To use programmatically, establish a session cookie first via the OAuth flow, or use the REST endpoints for non-streaming workflows.

**Sending a message:**
```json
{"message": "How many unavailable entities do I have?", "model": "google-gla:gemini-3-flash-preview"}
```

**Server events (streamed back):**

| Event type | Fields | Description |
|---|---|---|
| `session_created` | `session_id`, `title` | Sent once when first message auto-creates a session |
| `token` | `content` | Streamed text chunk from the LLM |
| `tool_call` | `name`, `args` | The agent is calling a tool |
| `tool_result` | `name`, `content` | Result returned from the tool (truncated to 500 chars) |
| `done` | — | Response complete, ready for next message |
| `error` | `content` | An error occurred |

A typical exchange looks like:
1. You send `{"message": "...", "model": "..."}`
2. You receive zero or more `tool_call` → `tool_result` pairs
3. You receive `token` events as the LLM streams its response
4. You receive `done`

The connection stays open for multi-turn conversation. Send another message to continue.

### Tokens

Manage your access tokens programmatically.

```
GET /api/tokens
```
Returns: `[{"id": "...", "name": "...", "created_at": "...", "last_used": "..."}]`

```
POST /api/tokens
```
Body: `{"name": "my-other-agent"}`
Returns: `{"id": "...", "name": "...", "token": "haa_...", "created_at": "...", "last_used": null}`

The `token` field is only returned once at creation time.

```
DELETE /api/tokens/{token_id}
```
Revokes a token permanently.

## Agent Capabilities

The HA Agent has access to these Home Assistant tools. You don't call them directly — describe what you need in natural language and the agent will select the right tools.

| Tool | What it does |
|---|---|
| `list_entities` | List entities with optional domain/state/keyword filters. Returns domain summary when unfiltered. |
| `get_entity_details` | Full state and attributes for a single entity |
| `get_entity_history` | Recent state changes for an entity (default 24h) |
| `search_entities` | Fuzzy search entities by name or ID |
| `list_automations` | List automations with optional keyword/state filter |
| `get_automation_config` | Full YAML config for an automation |
| `create_automation` | Create a new automation with triggers, conditions, and actions |
| `update_automation` | Update an existing automation's config |
| `list_scripts` | List scripts with optional keyword filter |
| `list_services` | List available HA services by domain |
| `find_unavailable_entities` | Find entities in unavailable/unknown state |
| `find_stale_entities` | Find entities that haven't changed state recently |
| `find_unused_automations` | Find automations that haven't triggered recently |
| `get_error_log` | Recent Home Assistant error log entries |
| `render_template` | Evaluate a Jinja2 template against HA state |
| `check_config` | Validate HA configuration files |
| `remove_entity` | Remove an entity from the HA registry |

## Example Prompts

These are natural language messages you can send to the agent:

- `"How many entities do I have?"` — returns a domain-level summary
- `"Show me all unavailable light entities"` — filtered entity search
- `"What automations reference the kitchen motion sensor?"` — cross-references automations
- `"Find entities that haven't changed in 48 hours"` — stale entity detection
- `"Show me the config for automation.morning_lights"` — inspect automation YAML
- `"Create an automation that turns off all lights at midnight"` — creates a real automation in HA
- `"What errors are in the HA log?"` — recent error log
- `"List services in the light domain"` — available service calls

## Example: Python Integration

```python
import asyncio
import json
import httpx
import websockets

BASE = "http://localhost:8000"
WS_BASE = "ws://localhost:8000"
TOKEN = "haa_your_token_here"
HEADERS = {"Authorization": f"Bearer {TOKEN}"}
MODEL = "google-gla:gemini-3-flash-preview"


def query_sessions():
    """List all sessions via REST."""
    resp = httpx.get(f"{BASE}/api/sessions", headers=HEADERS)
    return resp.json()


def get_session_messages(session_id: str):
    """Get full message history for a session."""
    resp = httpx.get(f"{BASE}/api/sessions/{session_id}", headers=HEADERS)
    return resp.json()


def create_session(title: str):
    """Create a new chat session."""
    resp = httpx.post(
        f"{BASE}/api/sessions",
        headers=HEADERS,
        json={"title": title},
    )
    return resp.json()
```

## Notes

- The agent maintains multi-turn context within a session. For follow-up questions, reuse the same session.
- Tool results in the streamed response are truncated to 500 characters. Use `GET /api/sessions/{id}` to retrieve full stored messages.
- The agent is instructed to always use tools for real data — it will not fabricate entity IDs or states.
- Model selection is per-message. You can switch models mid-conversation.
