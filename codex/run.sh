#!/usr/bin/with-contenv bashio
# shellcheck shell=bash

set -euo pipefail

# Graceful shutdown
cleanup() {
  bashio::log.info "Shutting down ttyd..."
  kill -TERM "$TTYD_PID" 2>/dev/null || true
  wait "$TTYD_PID" 2>/dev/null || true
}
trap cleanup SIGTERM SIGINT

port=8000
title="OpenAI Codex"

bashio::log.info "Starting ttyd terminal for Codex on port ${port} (Ingress enabled)"

# Persist Codex sessions across container restarts
mkdir -p /data/.codex-sessions
mkdir -p /root/.codex
ln -sfn /data/.codex-sessions /root/.codex/sessions

# Read configuration from Home Assistant Supervisor
OPENAI_API_KEY="$(bashio::config 'openai_api_key')"
CODEX_MODEL="$(bashio::config 'model')"
FONT_SIZE="$(bashio::config 'font_size')"

if [[ -z "${OPENAI_API_KEY}" ]]; then
  bashio::log.warning "No OpenAI API key configured. Set it in the add-on settings."
elif [[ ! "${OPENAI_API_KEY}" =~ ^sk- ]]; then
  bashio::log.warning "API key does not start with 'sk-'. Please verify your key."
fi

bashio::log.info "OPENAI_API_KEY: ${OPENAI_API_KEY:+***SET***}"
bashio::log.info "CODEX_MODEL: ${CODEX_MODEL:-<default>}"

# TTYD environment variables
export TTYD_PORT=${port}
export TTYD_TITLE=${title}
export TTYD_FONT_SIZE=${FONT_SIZE:-18}

# OpenAI API key environment variable
CODEX_RESUME_LAST="$(bashio::config 'resume_last_session')"
CODEX_WORKING_DIR="$(bashio::config 'working_directory')"

export OPENAI_API_KEY
export CODEX_MODEL
export CODEX_RESUME_LAST
export CODEX_WORKING_DIR="${CODEX_WORKING_DIR:-/config}"

ttyd \
  --interface 0.0.0.0 \
  --port "${TTYD_PORT}" \
  --check-origin \
  --writable \
  -t "titleFixed=${TTYD_TITLE}" \
  -t "fontSize=${TTYD_FONT_SIZE}" \
  env bash -c "/codex.sh" &
TTYD_PID=$!
wait "$TTYD_PID"
