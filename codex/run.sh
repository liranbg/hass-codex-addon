#!/usr/bin/with-contenv bashio

set -euo pipefail

port=8000
title="OpenAI Codex"
fontSize=18

# Read configuration from Home Assistant Supervisor
OPENAI_API_KEY="$(bashio::config 'openai_api_key')"
CODEX_MODEL="$(bashio::config 'model')"

bashio::log.info "OPENAI_API_KEY: ${OPENAI_API_KEY:+***SET***}"
bashio::log.info "CODEX_MODEL: ${CODEX_MODEL:-<default>}"
bashio::log.info "Starting ttyd terminal for Codex on port ${port} (Ingress enabled)"

# TTYD environment variables
export TTYD_PORT=${port}
export TTYD_TITLE=${title}
export TTYD_FONT_SIZE=${fontSize}

# OpenAI API key environment variable
export OPENAI_API_KEY
export CODEX_MODEL

exec ttyd \
  --interface 0.0.0.0 \
  --port "${TTYD_PORT}" \
  --check-origin \
  --writable \
  -t "titleFixed=${TTYD_TITLE}" \
  -t "fontSize=${TTYD_FONT_SIZE}" \
  env bash -c "/codex.sh"
