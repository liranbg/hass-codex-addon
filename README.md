## Home Assistant Add-on: OpenAI Codex (Web Terminal)

This repository contains a Home Assistant add-on that runs the **OpenAI Codex CLI** behind **Home Assistant Ingress**, exposing a web-based terminal in the Home Assistant UI.

The add-on format follows Home Assistant’s add-on development docs: [Developing an add-on](https://developers.home-assistant.io/docs/add-ons/).

### What you get

- A **terminal in Home Assistant** (Ingress) powered by `ttyd`
- The **`codex` CLI** running in **full-auto mode**
- Direct access to your **Home Assistant config directory** (`/config`)

### Install (as an add-on repository)

1. In Home Assistant: **Settings → Add-ons → Add-on Store**
2. Open the menu (⋮) → **Repositories**
3. Add this repository URL:
   ```
   https://github.com/liranbg/hass-codex-addon
   ```
4. Refresh and install **OpenAI Codex (Terminal)** add-on.

### Configure

1. Set `openai_api_key` in the add-on configuration (get one from [OpenAI Platform](https://platform.openai.com/api-keys)).
2. Optionally set a `model` (e.g., `gpt-4o`).
3. Start the add-on.
4. Click **Open Web UI** or find it in the sidebar.

### Usage

The add-on automatically starts Codex in full-auto mode with access to your Home Assistant configuration.

- Working directory: `/config` (your HA config folder)
- When Codex exits, press Enter to restart or type `exit` to quit
