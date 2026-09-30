# Changelog

## 0.1.1

- Add review_approvals (regular or approve) and allow_internet_access options.
- Keep the workspace-write sandbox in both approval modes; approve uses Codex's automatic reviewer.
- Preserve regular approval prompts and disabled sandbox internet access by default.

## 0.1.0

- Start versioned releases with pre-built images for amd64 and aarch64.
- Bundle Codex CLI 0.159.2.
- Offer Home Assistant updates after both release images have been published.
- Preserve existing add-on configuration and session data when upgrading from dev.
