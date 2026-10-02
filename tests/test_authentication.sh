#!/usr/bin/env bash
# Exercise persistent credentials using the bundled CLI and recreated containers.
set -euo pipefail

IMAGE="${1:-hass-codex-addon:dev}"
# A Docker volume avoids root-owned bind-mount files on Linux CI runners.
AUTH_DATA=$(docker volume create)
trap 'docker volume rm "${AUTH_DATA}" >/dev/null' EXIT

# Run the real startup script, replacing only Supervisor config and ttyd.
for phase in first second; do
  docker run --rm \
    -v "${AUTH_DATA}:/data" \
    -e TEST_PHASE="${phase}" \
    --entrypoint bash "${IMAGE}" -ec '
      cat > /tmp/bashio-stub.sh <<"STUB"
bashio::log.info() { :; }
bashio::log.warning() { :; }
bashio::config() { :; }
STUB
      mkdir -p /tmp/test-bin
      cat > /tmp/test-bin/ttyd <<"STUB"
#!/usr/bin/env bash
set -euo pipefail
[[ "$CODEX_HOME" == /data/.codex ]]
[[ -L "$CODEX_HOME/sessions" ]]
[[ ! -f /root/.codex/auth.json ]]
if [[ "$TEST_PHASE" == first ]]; then
  # API-key login caches locally; this placeholder never sends an API request.
  printf "%s\n" sk-test-persistence | codex -c '\''cli_auth_credentials_store="file"'\'' login --with-api-key
  test -f "$CODEX_HOME/auth.json"
else
  codex -c '\''cli_auth_credentials_store="file"'\'' login status
  grep -q sk-test-persistence "$CODEX_HOME/auth.json"
fi
STUB
      chmod +x /tmp/test-bin/ttyd
      export PATH="/tmp/test-bin:$PATH" BASH_ENV=/tmp/bashio-stub.sh
      bash /run.sh
    '
done

echo "PASS: bundled Codex reuses credentials after container recreation"
