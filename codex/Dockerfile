ARG BUILD_FROM=ghcr.io/home-assistant/aarch64-base:latest

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

# Install Codex CLI
RUN npm install -g @openai/codex

WORKDIR /workspace

COPY run.sh /run.sh
COPY codex.sh /codex.sh

CMD ["/run.sh"]
