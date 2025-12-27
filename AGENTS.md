# AGENTS.md

## Project Overview

This is a **Home Assistant add-on** that provides the OpenAI Codex CLI inside a web-based terminal accessible through Home Assistant's Ingress system.


## Project Structure

```
hass-codex-addon/
├── .devcontainer/         # VS Code devcontainer configuration
│   └── devcontainer.json  # Container definition for local testing
├── .vscode/               # VS Code tasks
│   └── tasks.json         # "Start Home Assistant" task
├── codex/                 # The add-on directory
│   ├── config.yaml        # Add-on metadata, options, and schema
│   ├── Dockerfile         # Container build definition
│   ├── run.sh             # Entrypoint script (starts ttyd)
│   ├── DOCS.md            # User-facing documentation
│   └── CHANGELOG.md       # Version history
├── repository.yaml        # Home Assistant repository metadata
└── README.md              # Repository overview
```

## Key Files

| File | Purpose |
|------|---------|
| `codex/config.yaml` | Defines add-on name, version, architecture, Ingress settings, and user options (`openai_api_key`, `model`) |
| `codex/Dockerfile` | Builds the container with Node.js, ttyd, git, and the Codex CLI |
| `codex/run.sh` | Reads config via bashio, sets environment variables, starts ttyd on port 8000 |
| `repository.yaml` | Declares this repo as a Home Assistant add-on repository |

## Guidelines for Modifications

1. **Version bumps** – Update `version` in `codex/config.yaml` and document changes in `CHANGELOG.md`
2. **New options** – Add to both `options` and `schema` sections in `config.yaml`
3. **Docker changes** – Keep the image minimal; use Alpine packages (`apk add`)
4. **Ingress port** – Must match between `config.yaml` (`ingress_port`) and `run.sh` (ttyd `-p` flag)
5. **Secrets** – Never commit API keys; they are provided at runtime via Home Assistant config

## Testing Locally

### Option 1: VS Code Devcontainer (Recommended)

The fastest way to test with the full Home Assistant Supervisor environment:

1. Install the [Remote Containers](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers) VS Code extension
2. Open this repository in VS Code
3. When prompted, select "Reopen in Container" (or use Command Palette → "Rebuild and Reopen in Container")
4. Once the container starts, run **Terminal → Run Task → "Start Home Assistant"**
5. Access Home Assistant at `http://localhost:7123/`
6. The add-on will appear in **Settings → Add-ons → Local Add-ons**

### Option 2: Standalone Docker Build

Build and test the Docker image directly:

```bash
cd codex
docker build --build-arg BUILD_FROM="ghcr.io/home-assistant/amd64-base:latest" -t hass-codex-addon .
```

Run with a mock API key:

```bash
docker run -it --rm -e OPENAI_API_KEY="sk-test" -p 8000:8000 hass-codex-addon
```

Then open `http://localhost:8000` to verify the terminal works.
