#!/usr/bin/env bash
# Native CLI integration: no OpenAI requests, credentials, or external downloads.
set -euo pipefail
IMAGE="${1:-hass-codex-addon:dev}"
PROJECT_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
docker run --rm \
  -v "${PROJECT_ROOT}/tests:/tests:ro" \
  --entrypoint timeout "${IMAGE}" 180 python3 /tests/plugin_container.py
