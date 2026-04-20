#!/usr/bin/with-contenv sh
# with-contenv makes s6's container environment (including SUPERVISOR_TOKEN)
# available to this script. Without it, SUPERVISOR_TOKEN is empty because
# s6 stores supervisor-injected vars in its own env dir, not as plain Docker vars.

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
    GEMINI_MODEL=$(read_option gemini_model "gemini-3.1-flash-lite-preview")
    PREFERRED_MODEL=$(read_option preferred_model "")
else
    OLLAMA_HOST=""
    GEMINI_API_KEY=""
    GEMINI_MODEL="gemini-3.1-flash-lite-preview"
    PREFERRED_MODEL=""
fi

export HASS_URL="http://supervisor/core"
export HASS_TOKEN="${SUPERVISOR_TOKEN}"
export OLLAMA_HOST="${OLLAMA_HOST}"
export GEMINI_API_KEY="${GEMINI_API_KEY}"
export GEMINI_MODEL="${GEMINI_MODEL}"
export PREFERRED_MODEL="${PREFERRED_MODEL}"
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
