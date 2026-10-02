# Changelog

## 0.1.3

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
