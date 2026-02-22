#!/usr/bin/with-contenv bashio

# Load addon options (bashio::config returns empty string for null values)
OLLAMA_HOST=$(bashio::config 'ollama_host')
GEMINI_API_KEY=$(bashio::config 'gemini_api_key')
GEMINI_MODEL=$(bashio::config 'gemini_model')

export HASS_URL="http://supervisor/core"
export HASS_TOKEN="${SUPERVISOR_TOKEN}"
export OLLAMA_HOST="${OLLAMA_HOST}"
export GEMINI_API_KEY="${GEMINI_API_KEY}"
export GEMINI_MODEL="${GEMINI_MODEL:-gemini-3-flash-preview}"
export ADDON_MODE="true"
export DB_PATH="/data/hass_agent.db"
export FRONTEND_DIR="/app/frontend/dist"

# Generate and persist a session secret across restarts
SECRET_FILE="/data/session_secret"
if [ ! -f "${SECRET_FILE}" ]; then
    python3 -c "import secrets; print(secrets.token_hex(32))" > "${SECRET_FILE}"
fi
export SESSION_SECRET="$(cat "${SECRET_FILE}")"

bashio::log.info "Starting HA Agent..."
bashio::log.info "Ollama host: ${OLLAMA_HOST:-not set}"
bashio::log.info "Gemini model: ${GEMINI_MODEL}"

cd /app
exec .venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
