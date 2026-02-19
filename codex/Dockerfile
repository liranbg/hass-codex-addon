ARG BUILD_FROM=ghcr.io/home-assistant/aarch64-base:latest

# ── Build stage: install Codex CLI ──
# hadolint ignore=DL3006
FROM ${BUILD_FROM} AS builder

# hadolint ignore=DL3018
RUN apk add --no-cache nodejs npm \
  && npm install -g @openai/codex@0.104.0 \
  && npm cache clean --force

# ── Runtime stage ──
# hadolint ignore=DL3006
FROM ${BUILD_FROM}

ARG BUILD_ARCH

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Base runtime deps
# hadolint ignore=DL3018
RUN apk add --no-cache \
    bash \
    ca-certificates \
    curl \
    git \
    jq \
    nodejs \
    npm \
    openssh-client \
    ttyd \
    python3 \
    vim

# Copy Codex CLI from builder and recreate symlink
COPY --from=builder /usr/local/lib/node_modules/@openai/codex /usr/local/lib/node_modules/@openai/codex
RUN ln -s ../lib/node_modules/@openai/codex/bin/codex.js /usr/local/bin/codex

# Install Home Assistant CLI
ADD https://github.com/home-assistant/cli/releases/latest/download/ha_${BUILD_ARCH} /usr/local/bin/ha
RUN chmod +x /usr/local/bin/ha && ha --help

WORKDIR /config

COPY run.sh codex.sh AGENTS.tmpl.md /

HEALTHCHECK --interval=30s --timeout=3s \
  CMD curl -f http://localhost:8000/ || exit 1

CMD ["/run.sh"]
