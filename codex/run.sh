#!/usr/bin/with-contenv bashio
# shellcheck shell=bash

set -euo pipefail

# Graceful shutdown
CHILD_PID=""
cleanup() {
  trap '' SIGTERM SIGINT
  bashio::log.info "Shutting down Codex add-on..."
  if [[ -n "${CHILD_PID}" ]]; then
    kill -TERM "${CHILD_PID}" 2>/dev/null || true
    wait "${CHILD_PID}" 2>/dev/null || true
  fi
  exit 0
}
trap cleanup SIGTERM SIGINT

port=8000
title="OpenAI Codex"

bashio::log.info "Starting ttyd terminal for Codex on port ${port} (Ingress enabled)"

# Persist credentials, configuration, and Codex state across container recreation.
export CODEX_HOME=/data/.codex
# Migrate once, so logging out cannot resurrect a stale legacy credential.
if [[ ! -d "${CODEX_HOME}" ]]; then
  mkdir -p "${CODEX_HOME}"
  for file in auth.json config.toml; do
    if [[ -f "/root/.codex/${file}" ]]; then
      cp "/root/.codex/${file}" "${CODEX_HOME}/${file}"
    fi
  done
fi
chmod 700 "${CODEX_HOME}"
if [[ -f "${CODEX_HOME}/auth.json" ]]; then
  chmod 600 "${CODEX_HOME}/auth.json"
fi

# Keep existing session history at its original persistent location.
mkdir -p /data/.codex-sessions
ln -sfn /data/.codex-sessions "${CODEX_HOME}/sessions"

# Read configuration from the Supervisor options file when available. This keeps
# startup deterministic in container tests and avoids unnecessary Supervisor API
# calls before the terminal starts.
addon_config() {
  local key="$1"
  if [[ -f /data/options.json ]]; then
    jq -r --arg key "${key}" '.[$key] // empty' /data/options.json
  else
    bashio::config "${key}"
  fi
}

OPENAI_API_KEY="$(addon_config 'openai_api_key')"
CODEX_MODEL="$(addon_config 'model')"
FONT_SIZE="$(addon_config 'font_size')"

if [[ -z "${OPENAI_API_KEY}" ]]; then
  bashio::log.info "No API key configured; Codex will reuse its saved login or prompt you to sign in."
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
CODEX_RESUME_LAST="$(addon_config 'resume_last_session')"
CODEX_WORKING_DIR="$(addon_config 'working_directory')"
CODEX_REVIEW_APPROVALS="$(addon_config 'review_approvals')"
CODEX_ALLOW_INTERNET_ACCESS="$(addon_config 'allow_internet_access')"

export OPENAI_API_KEY
export CODEX_MODEL
export CODEX_RESUME_LAST
export CODEX_WORKING_DIR="${CODEX_WORKING_DIR:-/config}"
export CODEX_REVIEW_APPROVALS="${CODEX_REVIEW_APPROVALS:-approve}"
export CODEX_ALLOW_INTERNET_ACCESS="${CODEX_ALLOW_INTERNET_ACCESS:-true}"

# Apply preset preferences once per start; Codex manages plugin installation.
python3 /manage-plugins.py /data/options.json &
CHILD_PID=$!
wait "${CHILD_PID}"
CHILD_PID=""

ttyd \
  --interface 0.0.0.0 \
  --port "${TTYD_PORT}" \
  --check-origin \
  --writable \
  -t "titleFixed=${TTYD_TITLE}" \
  -t "fontSize=${TTYD_FONT_SIZE}" \
  env bash -c "/codex.sh" &
CHILD_PID=$!
wait "${CHILD_PID}"
