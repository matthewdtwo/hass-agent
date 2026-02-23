#!/bin/sh
# Read addon options from /data/options.json directly with Python.
# SUPERVISOR_TOKEN is injected by the HA supervisor as a plain Docker env var
# so we don't need s6/with-contenv at all.

OPTIONS="/data/options.json"

read_option() {
    key="$1"
    default="$2"
    python3 -c "
import json, sys
try:
    v = json.load(open('${OPTIONS}')).get('${key}')
    print(v if v else '${default}')
except Exception:
    print('${default}')
" 2>/dev/null
}

if [ -f "$OPTIONS" ]; then
    OLLAMA_HOST=$(read_option ollama_host "")
    GEMINI_API_KEY=$(read_option gemini_api_key "")
    GEMINI_MODEL=$(read_option gemini_model "gemini-2.0-flash")
else
    OLLAMA_HOST=""
    GEMINI_API_KEY=""
    GEMINI_MODEL="gemini-2.0-flash"
fi

export HASS_URL="http://supervisor/core"
export HASS_TOKEN="${SUPERVISOR_TOKEN}"
export OLLAMA_HOST="${OLLAMA_HOST}"
export GEMINI_API_KEY="${GEMINI_API_KEY}"
export GEMINI_MODEL="${GEMINI_MODEL}"
export ADDON_MODE="true"
export DB_PATH="/data/hass_agent.db"
export FRONTEND_DIR="/app/frontend/dist"

# Generate and persist a session secret across restarts
SECRET_FILE="/data/session_secret"
if [ ! -f "${SECRET_FILE}" ]; then
    python3 -c "import secrets; print(secrets.token_hex(32))" > "${SECRET_FILE}"
fi
export SESSION_SECRET="$(cat "${SECRET_FILE}")"

echo "Starting HA Agent (Gemini model: ${GEMINI_MODEL}, Ollama: ${OLLAMA_HOST:-not set})"

cd /app
exec .venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
