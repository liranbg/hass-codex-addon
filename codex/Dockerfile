ARG BUILD_FROM=ghcr.io/home-assistant/aarch64-base:latest
ARG BUILD_ARCH

FROM ${BUILD_FROM}

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Base runtime deps
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
    vim

# Install Home Assistant CLI
ARG BUILD_ARCH
ADD https://github.com/home-assistant/cli/releases/latest/download/ha_${BUILD_ARCH} /usr/local/bin/ha
RUN chmod +x /usr/local/bin/ha && ha --help

# Install Codex CLI
RUN npm install -g @openai/codex@^0.79.0

WORKDIR /config

COPY run.sh /run.sh
COPY codex.sh /codex.sh
COPY AGENTS.tmpl.md /AGENTS.tmpl.md

CMD ["/run.sh"]
