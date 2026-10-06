# Changelog

## 0.2.1

- Update Codex CLI from 0.160.0 to 0.160.1.

## 0.2.0

- Restore Home Assistant update discovery after repository rules blocked release metadata publication; automatically publish future metadata updates after image publication and checks on the metadata commit.
- Add plugin_presets for public GitHub marketplaces; Codex handles cloning, plugin installation, skills, and bundled MCP registration.
- Refresh branches and tags on add-on restart, support full commit pins, and retain cached plugins when updates fail.
- Preserve manually installed plugins and standalone MCP connections when removing presets; persist MCP OAuth logins across restarts.

## 0.1.4

- Persist Codex authentication and configuration in the add-on data directory; reuse the last login method across restarts and updates.

## 0.1.3

- Replace the bundled playbook with verified Home Assistant editing, validation, and runtime safety guidelines; inspect installation-specific includes and storage settings.
- Refresh managed AGENTS.md from bundled defaults when opening the terminal; support optional AGENTS.extend.md and back up existing instructions during migration.

## 0.1.2

- Update Codex CLI from 0.159.2 to 0.160.0.

## 0.1.1

- Run new and resumed Codex sessions with --no-daemon to avoid background app-server process start-time failures in Home Assistant containers.
- Add review_approvals (ask or approve) and allow_internet_access options.
- Keep the workspace-write sandbox in both approval modes; approve uses Codex's automatic reviewer.
- Enable automatic approval review and sandbox internet access by default; select ask for manual review.

## 0.1.0

- Start versioned releases with pre-built images for amd64 and aarch64.
- Bundle Codex CLI 0.159.2.
- Offer Home Assistant updates after both release images have been published.
- Preserve existing add-on configuration and session data when upgrading from dev.
