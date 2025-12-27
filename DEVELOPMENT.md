# DEVELOPMENT.md

## Goal

This repository is a **Home Assistant add-on** that runs the OpenAI Codex CLI inside a **web terminal (ttyd)** exposed via Home Assistant **Ingress**.

This document is for **local development**. Each section is designed to be **run manually** and includes a quick “verify” step.

Assumption: commands are run from the **repository root** unless stated otherwise.

## Project model (what’s running where)

- **Add-on container**: built from [`codex/Dockerfile`](codex/Dockerfile)
- **Runtime entrypoint in HA**: [`codex/run.sh`](codex/run.sh)
  - Uses `bashio` to read add-on config (available **only** under the HA Supervisor environment)
  - Starts `ttyd` on **port 8000**
- **Add-on metadata/options**: [`codex/config.yaml`](codex/config.yaml)
  - Ingress enabled, `ingress_port: 8000`


## Prerequisites

- Docker Desktop (or Docker Engine) running locally
- (Optional, for real Codex calls) an `OPENAI_API_KEY`

## Local container testing

### Build the image

From repo root:

```bash

# armhf: ghcr.io/home-assistant/armhf-base:latest
# aarch64: ghcr.io/home-assistant/aarch64-base:latest
# amd64: ghcr.io/home-assistant/amd64-base:latest
# i386: ghcr.io/home-assistant/i386-base:latest
docker build \
  -f codex/Dockerfile \
  --build-arg BUILD_FROM="ghcr.io/home-assistant/aarch64-base:latest" \
  -t hass-codex-addon:dev \
  codex/
```

Verify (expected: image exists):

```bash
docker images hass-codex-addon:dev
```

### Run ttyd in detached mode (standalone)

```bash
docker rm -f hass-codex-addon-dev >/dev/null 2>&1 || true

docker run -d --rm --name hass-codex-addon-dev \
  -v $(pwd)/.local_run:/data \
  -p 8000:8000 \
  hass-codex-addon:dev
```

Verify (expected: HTTP 200):

```bash
curl -fsS -o /dev/null -w "HTTP=%{http_code}\n" http://localhost:8000/
```

Debug (expected: log line includes “Listening on port: 8000”):

```bash
docker logs --tail 50 hass-codex-addon-dev
```

Stop:

```bash
docker rm -f hass-codex-addon-dev
```

## Iterative development (fast edit → test loop)

### When you need a rebuild

- **Dockerfile changes**: always rebuild the image
- **`run.sh` changes**:
  - Standalone test: rebuild (because `run.sh` is `COPY`’d into the image)
  - HA test: rebuild the add-on (Supervisor rebuild)
- **`config.yaml` changes**: rebuild/reload add-on metadata in HA (and often rebuild)

### Fast rebuild + rerun

#### Run once
```bash

docker build \
  -f codex/Dockerfile \
  --build-arg BUILD_FROM="ghcr.io/home-assistant/aarch64-base:latest" \
  -t hass-codex-addon:dev \
  codex/

docker rm -f hass-codex-addon-dev >/dev/null 2>&1 || true

docker run -d --rm --name hass-codex-addon-dev \
  -v $(pwd)/.local_run:/data \
  -p 8000:8000 \
  hass-codex-addon:dev

```

#### Run iteratively

For rapid iteration on shell scripts **without rebuilding** the image:

```bash
# Copy updated scripts into the running container
docker cp ./codex/codex.sh hass-codex-addon-dev:/codex.sh

```

> **Note**: This only works for script changes. Dockerfile changes (new packages, build steps) always require a full rebuild.

---

## Local configuration

The add-on reads configuration via `bashio`. For **standalone local testing** (without Home Assistant Supervisor), `run.sh` falls back to `/data/options.json`.

### Setup local options

Create the `.local_run/` directory and options file:

```bash
mkdir -p .local_run

cat > .local_run/options.json << 'EOF'
{
    "openai_api_key": "sk-your-key-here",
    "model": ""
}
EOF
```

The `docker run` command mounts this directory to `/data`, making the config available to `run.sh`.

### Configuration options

| Option | Required | Description |
|--------|----------|-------------|
| `openai_api_key` | Yes | Your OpenAI API key |
| `model` | No | Model override (e.g., `o3-mini`). Empty uses Codex default |

---

## Architecture overview

```
┌─────────────────────────────────────────────────────────────┐
│ Browser                                                     │
│   └── http://localhost:8000/                                │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│ ttyd (port 8000)                                            │
│   └── spawns bash → /codex.sh                               │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│ /codex.sh                                                   │
│   1. Logs into Codex CLI with OPENAI_API_KEY                │
│   2. Launches `codex --full-auto [-m MODEL]`                │
└─────────────────────────────────────────────────────────────┘
```

---

## Troubleshooting

### Container exits immediately

Check logs for errors:

```bash
docker logs hass-codex-addon-dev
```

Common causes:
- Missing `/data/options.json` → create `.local_run/options.json`
- Invalid JSON in options file → validate with `jq . .local_run/options.json`

### ttyd not accessible

```bash
# Check container is running
docker ps | grep hass-codex-addon-dev

# Check port binding
docker port hass-codex-addon-dev

# Test connectivity
curl -v http://localhost:8000/
```

### Codex login fails

Verify your API key is valid:

```bash
docker exec -it hass-codex-addon-dev sh -c 'echo $OPENAI_API_KEY | head -c 20'
```

### Shell into running container

```bash
docker exec -it hass-codex-addon-dev /bin/bash
```

---

## Testing checklist

Before committing changes:

- [ ] `docker build` succeeds
- [ ] Container starts without errors (`docker logs`)
- [ ] ttyd web UI loads at `http://localhost:8000/`
- [ ] Codex CLI launches inside the terminal
- [ ] (If API key provided) Codex authenticates successfully
