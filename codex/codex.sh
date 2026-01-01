#!/usr/bin/env bash
set -euo pipefail

cd /config

# Ensure AGENTS.md exists in working directory
if [[ ! -f "AGENTS.md" ]]; then
  echo "Creating AGENTS.md from template..."
  cp /AGENTS.tmpl.md AGENTS.md
fi

clear
echo "Initializing OpenAI Codex..."

# if OPENAI_API_KEY is set, login
if [[ -n "${OPENAI_API_KEY:-}" ]]; then
  echo "Authenticating with OpenAI API key..."
  echo "${OPENAI_API_KEY}" | codex login --with-api-key
  if codex login status 2>/dev/null | grep -q "Logged in"; then
    echo "✓ Logged in successfully"
  else
    echo "⚠ Login status could not be verified"
  fi
else
  echo "⚠ No OPENAI_API_KEY set. Configure it in the add-on settings."
  sleep 5
fi

echo ""
sleep 1

# Launch codex in an interactive loop so terminal stays open
while true; do
  clear
  echo "Working directory: $(pwd)"
  echo ""
  
  if [[ -n "${CODEX_MODEL:-}" ]]; then
    node "$(which codex)" --full-auto -m "${CODEX_MODEL}" || true
  else
    node "$(which codex)" --full-auto || true
  fi
  
  echo ""
  echo "Codex session ended. Press Enter to restart, or type '!exit' to quit."
  read -r input
  if [[ "${input}" == "!exit" ]]; then
    echo "Goodbye!"
    break
  fi
done
