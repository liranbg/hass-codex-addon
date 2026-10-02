#!/usr/bin/env bash
set -euo pipefail

# Graceful shutdown on signals
cleanup() {
  echo ""
  echo "Shutting down..."
  exit 0
}
trap cleanup SIGTERM SIGINT

cd "${CODEX_WORKING_DIR:-/config}"

# Keep permissions explicit so local Codex config cannot override add-on options.
case "${CODEX_REVIEW_APPROVALS:-approve}" in
  ask) approvals_reviewer=user ;;
  approve) approvals_reviewer=auto_review ;;
  *) echo "ERROR: review_approvals must be ask or approve."; exit 1 ;;
esac
case "${CODEX_ALLOW_INTERNET_ACCESS:-true}" in
  true|false) internet_access="${CODEX_ALLOW_INTERNET_ACCESS:-true}" ;;
  *) echo "ERROR: allow_internet_access must be true or false."; exit 1 ;;
esac

clear

# Refresh bundled guidance while preserving pre-existing user instructions.
agents_marker='<!-- Managed by hass-codex-addon; put personal instructions in AGENTS.extend.md. -->'
if [[ -L AGENTS.md || ( -e AGENTS.md && ! -f AGENTS.md ) ]]; then
  echo "ERROR: AGENTS.md must be a regular file. Move personal instructions to AGENTS.extend.md."
  exit 1
fi
if [[ -f AGENTS.md ]] && [[ "$(head -n 1 AGENTS.md)" != "${agents_marker}" ]]; then
  agents_backup="$(mktemp ./AGENTS.md.backup.XXXXXX)"
  cp AGENTS.md "${agents_backup}"
  echo "Saved existing AGENTS.md to ${agents_backup}."
  if [[ ! -e AGENTS.extend.md && ! -L AGENTS.extend.md ]]; then
    cp AGENTS.md AGENTS.extend.md
    echo "Migrated existing instructions to AGENTS.extend.md; review it for outdated defaults."
  else
    echo "Keeping existing AGENTS.extend.md. Merge any personal instructions from ${agents_backup} into it."
  fi
fi
if ! cmp -s /AGENTS.tmpl.md AGENTS.md; then
  agents_tmp="$(mktemp ./AGENTS.md.tmp.XXXXXX)"
  if ! cp /AGENTS.tmpl.md "${agents_tmp}" || ! mv -f "${agents_tmp}" AGENTS.md; then
    rm -f "${agents_tmp}"
    echo "ERROR: Could not refresh AGENTS.md from the bundled template."
    exit 1
  fi
  echo "Updated managed AGENTS.md from bundled template."
fi

# Pre-flight: verify codex CLI is available
if ! command -v codex >/dev/null 2>&1; then
  echo "ERROR: Codex CLI not found. The add-on image may be corrupted."
  echo "Try rebuilding the add-on from the Home Assistant settings."
  sleep 30
  exit 1
fi

# Welcome message
echo "========================================="
echo "  OpenAI Codex — Home Assistant Add-on"
echo "========================================="
echo ""
echo "  Model:     ${CODEX_MODEL:-<default>}"
echo "  Directory:  $(pwd)"
if [[ "${CODEX_RESUME_LAST:-false}" == "true" ]]; then
  echo "  Session:    Resuming last session"
fi
echo ""
echo "  Type '!exit' after a session to quit."
echo "========================================="
echo ""

# Authenticate with OpenAI
if [[ -n "${OPENAI_API_KEY:-}" ]]; then
  echo "Authenticating with OpenAI API key..."
  if echo "${OPENAI_API_KEY}" | codex login --with-api-key 2>/dev/null; then
    if codex login status 2>/dev/null | grep -q "Logged in"; then
      echo "Logged in successfully."
    else
      echo "WARNING: Login status could not be verified."
    fi
  else
    echo "WARNING: Login failed. Please check your API key in the add-on settings."
  fi
else
  echo "WARNING: No OPENAI_API_KEY set. Configure it in the add-on settings."
  sleep 5
fi

echo ""
sleep 1

# Launch codex in an interactive loop so terminal stays open
while true; do
  codex_args=(
    # HA containers can prevent the daemon from reading its process start time.
    --no-daemon
    --sandbox workspace-write
    --ask-for-approval on-request
    -c "approvals_reviewer=\"${approvals_reviewer}\""
    -c "sandbox_workspace_write.network_access=${internet_access}"
  )
  if [[ -n "${CODEX_MODEL:-}" ]]; then
    codex_args+=(-m "${CODEX_MODEL}")
  fi
  if [[ "${CODEX_RESUME_LAST:-false}" == "true" ]]; then
    codex_args+=(resume --last)
  fi

  node "$(which codex)" "${codex_args[@]}" || true

  echo ""
  echo "Codex session ended. Press Enter to restart, or type '!exit' to quit."
  read -r input
  if [[ "${input}" == "!exit" ]]; then
    echo "Goodbye!"
    break
  fi
done
