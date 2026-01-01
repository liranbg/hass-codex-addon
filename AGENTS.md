# AGENTS.md

## Project Overview

This is a **Home Assistant add-on** that provides the OpenAI Codex CLI inside a web-based terminal accessible through Home Assistant's Ingress system.

## Project Structure

```
hass-codex-addon/
├── codex/                 # The add-on directory
│   ├── config.yaml        # Add-on metadata, options, and schema
│   ├── build.yaml         # Build configuration (base images per architecture)
│   ├── Dockerfile         # Container build definition
│   ├── run.sh             # Container entrypoint (reads config, starts ttyd)
│   ├── codex.sh           # Codex CLI wrapper (auth + interactive loop)
│   ├── DOCS.md            # User-facing documentation
│   └── AGENTS.tmpl.md     # Template for AI agents context
├── repository.yaml        # Home Assistant repository metadata
└── README.md              # Repository overview
```

## Key Files

| File                | Purpose                                                                                                    |
| ------------------- | ---------------------------------------------------------------------------------------------------------- |
| `codex/config.yaml` | Defines add-on name, version, architecture, Ingress settings, and user options (`openai_api_key`, `model`) |
| `codex/build.yaml`  | Specifies base Docker images for each supported architecture (aarch64, amd64, armv7)                       |
| `codex/Dockerfile`  | Builds the container with Node.js, ttyd, git, HA CLI, and the Codex CLI (`@openai/codex`)                  |
| `codex/run.sh`      | Reads config via bashio, exports `OPENAI_API_KEY` and `CODEX_MODEL`, starts ttyd on port 8000              |
| `codex/codex.sh`    | Handles Codex CLI authentication and runs an interactive loop with `codex --full-auto`                     |
| `repository.yaml`   | Declares this repo as a Home Assistant add-on repository                                                   |

## Guidelines for Modifications

1. **Version bumps** – Update `version` in `codex/config.yaml` and document changes in `CHANGELOG.md`
2. **New options** – Add to both `options` and `schema` sections in `config.yaml`
3. **Docker changes** – Keep the image minimal; use Alpine packages (`apk add`)
4. **Ingress port** – Must match between `config.yaml` (`ingress_port`) and `run.sh` (ttyd `-p` flag)
5. **Secrets** – Never commit API keys; they are provided at runtime via Home Assistant config

## Testing Locally

Build the Docker image manually for testing - following DEVELOPMENT.md

Then open `http://localhost:8000` to verify the terminal works.
