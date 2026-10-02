# DEVELOPMENT.md

## Goal

This repository is a **Home Assistant add-on** that runs the OpenAI Codex CLI inside a **web terminal (ttyd)** exposed via Home Assistant **Ingress**.

This document is for **local development**. Each section is designed to be **run manually** and includes a quick “verify” step.

Assumption: commands are run from the **repository root** unless stated otherwise.

## Project model (what's running where)

- **Add-on container**: built from [`codex/Dockerfile`](codex/Dockerfile)
  - Installs Node.js, ttyd, git, HA CLI, and `@openai/codex` CLI
- **Runtime entrypoint in HA**: [`codex/run.sh`](codex/run.sh)
  - Uses `bashio` to read add-on config (available **only** under the HA Supervisor environment)
  - Exports `OPENAI_API_KEY` and `CODEX_MODEL` environment variables
  - Applies plugin presets through [`codex/manage-plugins.py`](codex/manage-plugins.py) before opening the terminal
  - Starts `ttyd` on **port 8000**, which spawns [`codex/codex.sh`](codex/codex.sh)
- **Codex wrapper script**: [`codex/codex.sh`](codex/codex.sh)
  - Authenticates with OpenAI using `OPENAI_API_KEY`
  - Launches `codex --no-daemon --sandbox workspace-write --ask-for-approval on-request [-m MODEL]` in an interactive loop
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
  --build-arg BUILD_ARCH=aarch64 \
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
- **`run.sh` or `codex.sh` changes**:
  - Standalone test: rebuild (because scripts are `COPY`'d into the image), or use `docker cp` for quick iteration
  - HA test: rebuild the add-on (Supervisor rebuild)
- **`config.yaml` changes**: rebuild/reload add-on metadata in HA (and often rebuild)

### Fast rebuild + rerun

#### Run once

```bash

docker build \
  -f codex/Dockerfile \
  --build-arg BUILD_FROM=ghcr.io/home-assistant/aarch64-base:latest \
  --build-arg BUILD_ARCH=aarch64 \
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
docker cp ./codex/run.sh hass-codex-addon-dev:/run.sh
```

> **Note**: This only works for script changes. Dockerfile changes (new packages, build steps) always require a full rebuild. For `run.sh` changes to take effect, you need to restart the container.

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

| Option           | Required | Env Variable     | Description                                                           |
| ---------------- | -------- | ---------------- | --------------------------------------------------------------------- |
| `openai_api_key` | Yes      | `OPENAI_API_KEY` | Your OpenAI API key                                                   |
| `model`          | No       | `CODEX_MODEL`    | Model override (e.g., `gpt-5.1-codex-mini`). Empty uses Codex default                 |
| `review_approvals` | No | `CODEX_REVIEW_APPROVALS` | `approve` (default) uses automatic review; `ask` uses user review |
| `plugin_presets` | No | — | List of public GitHub marketplaces with `repository`, optional `ref`, and optional `plugin`; moving refs refresh before ttyd starts; defaults to `[]` |
| `allow_internet_access` | No | `CODEX_ALLOW_INTERNET_ACCESS` | Allow sandbox command networking; defaults to `true` |

---

## Plugin preset adapter

[`codex/manage-plugins.py`](codex/manage-plugins.py) is a startup adapter around the bundled Codex CLI's native plugin manager. It reads `plugin_presets` from `/data/options.json`, validates and groups entries by repository, and invokes `codex plugin marketplace add`, `marketplace upgrade`, `list`, `add`, and `remove` with JSON output. Codex performs all Git operations, manifest validation, cache updates, skill discovery, and bundled MCP registration. The adapter does not implement a separate skill registry or run a model session.

`/data/.codex/addon-plugin-presets.json` records each source's marketplace/ref and whether the adapter originally installed each plugin. It is saved atomically after successful installs. This ownership record prevents removing plugins the user already had. Removing a preset leaves its marketplace registered for browsing and unrelated installs.

Native `marketplace add --ref` selects the initial reference. Git's `check-ref-format` validates ref names. The bundled CLI has no command to change an existing marketplace's reference, so `set_ref()` changes only that marketplace's `ref` in Codex's `config.toml`, preserving other settings and file permissions. It then calls native `marketplace upgrade`; a failure restores the prior config. Moving refs refresh on every add-on start; full 40-character commit pins skip that refresh. Per-marketplace failures are logged and leave cached plugins available while other presets continue.

`apply()` starts a shared 30-second deadline before validation. Every child command receives only the remaining budget, and Git prompts are disabled. Commands run in their own process groups; a timeout kills the group, including Codex and Git descendants, before configuration rollback. `StartupTimeout` stops reconciliation before removal of any unvisited presets, and the entrypoint logs a warning while continuing to ttyd. Successful installs have already saved their ownership state, so a timeout can be retried safely on the next start.

`run.sh` runs the preset manager as a tracked child and waits for it before starting ttyd. SIGTERM/SIGINT interrupts that wait immediately, signals the child, waits for cleanup, and exits without opening the terminal. The manager terminates its active command group and rolls back a pending reference change when cancelled. Native global marketplace discovery can fail because of an unrelated broken manifest; the adapter then attempts each repository through scoped native add/list operations. Plugin selection matches Codex's ASCII, dot-separated name grammar, including names beginning with a hyphen.

The container stores Codex state under `/data/.codex`, and the interactive wrapper selects file storage for MCP OAuth credentials. Plugin MCP definitions still need any server-specific authentication or runtime dependencies. The add-on does not supply them.

Run unit checks and native lifecycle tests after building the image:

```bash
python3 -m unittest discover -s tests -p 'test_*.py'
ruff format codex/manage-plugins.py tests/test_plugins.py tests/plugin_container.py tests/test_authentication.py tests/test_permissions.py
ruff check codex/manage-plugins.py tests/test_plugins.py tests/plugin_container.py tests/test_authentication.py tests/test_permissions.py
bash tests/test_plugin_presets.sh hass-codex-addon:dev
```

The container test uses local Git fixtures through the real Codex CLI and actual startup script. It verifies plugin and MCP registration, skill discovery, branch updates without version bumps, commit pins, failed-reference rollback, and removal without losing manual plugins or MCP settings. It also exercises hexadecimal and punctuation ref names, dotted and leading-hyphen plugin names, isolation of a broken unrelated marketplace, the shared startup deadline, and SIGTERM/SIGINT during a stalled Git operation. It makes no OpenAI requests or external downloads.

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
│   2. Launches `codex --no-daemon --sandbox workspace-write --ask-for-approval on-request [-m MODEL]`                │
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

## Stable releases

`codex/VERSION` is the next intended add-on version, starting at `0.1.0`.
`codex/config.yaml` advertises the last successfully published version to Home
Assistant. These values deliberately differ while a release is pending. For
the initial migration, `config.yaml` stays at `dev` until the `0.1.0` images
are ready; the Release workflow then proposes its version and `image` URL in a PR.

For each release:

1. Advance `codex/VERSION` and add an entry to `codex/CHANGELOG.md` in your PR.
   Do not manually advance the version in `config.yaml` or add an image tag.
2. Merge the PR after CI passes. The Release workflow validates the merged
   commit again, including both architecture builds and the container tests.
3. The workflow publishes `ghcr.io/liranbg/hass-codex-addon/{arch}:VERSION`
   for amd64 and aarch64, with Home Assistant image labels.
4. It creates the `vVERSION` GitHub release and opens an `auto/publish-VERSION`
   PR updating the published version and image URL in `config.yaml`. The existing
   `CODEX_UPDATE_TOKEN` starts PR CI automatically. Merge that PR once the required
   checks pass; only then does Home Assistant see the update. The resulting main
   workflow sees no pending version and skips image publication.
   If runtime changes land before the metadata PR merges, close that PR and
   advance `codex/VERSION` to publish the new source under a new release tag.

The daily Codex updater prepares the Dockerfile pin, a patch bump, and changelog
in one PR. You decide when to merge it. It also explicitly dispatches CI for
the bot-created branch. While a release is pending, it defers further updates
so another Codex version cannot overwrite the pending release.

For add-on changes unrelated to Codex, choose a patch, minor, or major bump in
`codex/VERSION` and document the changes yourself. Merges without a version
bump keep publishing the development image but do not create a stable release.

### Repository setup and recovery

- GitHub Actions must be allowed to create pull requests and write repository
  contents and packages. `CODEX_UPDATE_TOKEN` must be able to write repository
  contents and create pull requests, as for the daily updater. Release metadata
  goes through normal PR checks; no branch-protection bypass is needed.
- Both GHCR architecture packages must be **public** so Home Assistant can
  pull them without GitHub credentials. Check their package visibility before
  the first installation/update using pre-built images.
- A failed build leaves the advertised Home Assistant version unchanged.
  Fix the build and merge the fix, or rerun Release for the same commit.
- Release runs are serialized. If `main` advances during a build, the stale
  run stops before advertising its images; the newer run handles publication.
- If a GitHub release exists but the metadata PR could not be created, rerun
  that run after restoring token permissions. If `main` has since changed, advance
  `codex/VERSION` and its changelog; an existing release tag cannot be reused
  for a different source commit.
- To recover an older direct-push publication failure, verify both images and
  the release tag exist and that main's runtime files match the tagged source.
  Run `python3 scripts/release.py promote` and submit the metadata change through
  a checked PR. Do not advertise runtime changes that are absent from those images.
- You can manually run **Release** on `main` using GitHub Actions. No manual
  tag push is needed. Nothing is released merely by pushing a feature branch.

Local release automation checks (no Docker required):

```bash
python3 scripts/release.py check
python3 -m unittest discover -s tests -p 'test_*.py'
```
