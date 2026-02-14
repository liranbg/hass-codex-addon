# Improvement Plan for hass-codex-addon

## Phase 1: Bug Fixes & Must-Fix Issues

### 1.1 Architecture mismatch between build.yaml and config.yaml
- `codex/build.yaml` defines `armv7` but `codex/config.yaml` only lists `amd64` and `aarch64`
- **Action:** Remove `armv7` from `build.yaml` (Node.js/Codex support is poor on armv7), or add it to `config.yaml` if it's truly supported

### 1.2 CI workflow: missing `yq` installation
- `ci.yaml` and `publish.yaml` use `yq` to extract base images from `build.yaml` but never install it
- **Action:** Add a step to install `yq` (e.g., `pip install yq` or use `mikefarah/yq` action), or switch to a `jq`/`grep` approach that doesn't require `yq`

### 1.3 Docker image: clean APK cache
- Dockerfile installs packages but never cleans `/var/cache/apk/*`
- **Action:** Append `&& rm -rf /var/cache/apk/*` to the `apk add` line

---

## Phase 2: Security Improvements

### 2.1 API key leak prevention
- `codex.sh` pipes the API key to `codex login --with-api-key` via stdin; if login fails, error output could expose the key
- **Action:** Redirect stderr during the login command to avoid leaking the key in logs; add a generic "Login failed" message instead

### 2.2 API cost and rate-limit warnings
- Full-auto mode can consume API credits rapidly with no guardrails
- **Action:** Add a prominent warning in `DOCS.md` about potential costs; consider adding an optional `max_tokens` or `timeout` config option

### 2.3 Session data privacy
- Session files stored in `/data/.codex-sessions` may contain sensitive conversation history
- **Action:** Document this in `DOCS.md`; mention that session data persists across restarts and what it may contain

### 2.4 Input validation for API key
- `run.sh` doesn't validate the API key format before passing it to Codex
- **Action:** Add a basic check that the key is non-empty and starts with `sk-` before proceeding

---

## Phase 3: Docker Optimization

### 3.1 Multi-stage build
- Current Dockerfile is single-stage; npm global install pulls in build artifacts that aren't needed at runtime
- **Action:** Use a multi-stage build — install `@openai/codex` in a build stage, then copy only the necessary files to the final image

### 3.2 Combine COPY layers
- Multiple `COPY` commands create separate layers
- **Action:** Combine into a single `COPY run.sh codex.sh AGENTS.tmpl.md /`

### 3.3 Pin Alpine package versions
- Packages are installed without version pins, risking breakage on upstream changes
- **Action:** Pin major versions of critical packages (nodejs, npm, ttyd) for reproducibility

### 3.4 Add Docker HEALTHCHECK
- No health check exists; Home Assistant watchdog can't detect if ttyd has crashed
- **Action:** Add `HEALTHCHECK --interval=30s --timeout=3s CMD curl -f http://localhost:8000/ || exit 1`

---

## Phase 4: CI/CD Improvements

### 4.1 Run tests in CI
- `tests/test_resume_session.sh` exists but isn't executed in any workflow
- **Action:** Add a test job to `ci.yaml` that runs the test suite

### 4.2 Add linting
- No shellcheck or hadolint in CI
- **Action:** Add a lint job that runs `shellcheck` on all `.sh` files and `hadolint` on the Dockerfile

### 4.3 Release workflow
- Only unstable builds exist (`publish.yaml` tags `:unstable`); no versioned releases
- **Action:** Create a `release.yaml` workflow triggered by git tags (e.g., `v*`) that builds and pushes versioned images, and updates `config.yaml` version

### 4.4 Docker layer caching in CI
- Builds don't use Docker layer caching, making CI slower
- **Action:** Add `cache-from` and `cache-to` parameters to `docker/build-push-action`

---

## Phase 5: Configuration & Features

### 5.1 Configurable font size
- Font size is hardcoded to 18 in `run.sh`
- **Action:** Add `font_size` option to `config.yaml` (with default 18); read it via bashio in `run.sh`

### 5.2 Custom working directory
- Working directory is hardcoded to `/config`
- **Action:** Add `working_directory` option to `config.yaml` (default `/config`); pass it to `codex.sh`

### 5.3 Backup configuration
- No `backup` field in `config.yaml`
- **Action:** Add `backup: "hot"` or similar to exclude large session files from HA backups

### 5.4 Add CHANGELOG.md
- No changelog exists to track version history
- **Action:** Create `CHANGELOG.md` with entries for all existing releases

---

## Phase 6: UX Improvements

### 6.1 Improved welcome message
- Terminal opens with minimal info
- **Action:** Show add-on version, selected model, working directory, and key commands (e.g., `!exit` to quit) on startup

### 6.2 Session resume feedback
- No indication when resuming a previous session
- **Action:** Print a message like "Resuming last session..." when `CODEX_RESUME_LAST=true`

### 6.3 Error handling and recovery
- If `codex` binary is missing or login fails, errors are unclear
- **Action:** Add pre-flight checks in `codex.sh`: verify `codex` exists, verify login succeeded with clear error messages

### 6.4 Signal handling
- No cleanup handlers for SIGTERM/SIGINT
- **Action:** Add `trap` handlers in `run.sh` and `codex.sh` to clean up gracefully

---

## Phase 7: Documentation

### 7.1 Document session resume feature in DOCS.md
- The `resume_last_session` option exists but isn't covered in user-facing docs
- **Action:** Add a section to `DOCS.md` explaining session persistence and the resume option

### 7.2 Troubleshooting section
- No user-facing troubleshooting guide
- **Action:** Add common issues to `DOCS.md` (login failures, blank screen, model errors)

### 7.3 Usage examples
- No example automations or use cases
- **Action:** Add examples to `DOCS.md` (e.g., "Create a light automation", "Debug a failing sensor")

### 7.4 Add SECURITY.md
- No security policy for reporting vulnerabilities
- **Action:** Create `SECURITY.md` with disclosure guidelines
