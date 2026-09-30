## Home Assistant Add-on: OpenAI Codex (Web Terminal)

This repository contains a Home Assistant add-on that runs the **OpenAI Codex CLI** behind **Home Assistant Ingress**, exposing a web-based terminal in the Home Assistant UI.

The add-on format follows Home Assistant’s add-on development docs: [Developing an add-on](https://developers.home-assistant.io/docs/add-ons/).

### What you get

- A **terminal in Home Assistant** (Ingress) powered by `ttyd`
- The **`codex` CLI** with a **workspace-write sandbox** and configurable approval review
- Direct access to your **Home Assistant config directory** (`/config`)

### Install (as an add-on repository)

1. In Home Assistant: **Settings → Add-ons → Add-on Store**
2. Open the menu (⋮) → **Repositories**
3. Add this repository URL:
   ```
   https://github.com/liranbg/hass-codex-addon
   ```
4. Refresh and install **OpenAI Codex (Terminal)** add-on.

### Updates

Stable releases start at **0.1.0**. Home Assistant downloads pre-built images
for your architecture and offers updates when a new add-on version is published.
The bundled Codex CLI version is listed in [`codex/CHANGELOG.md`](codex/CHANGELOG.md).

Existing installations of this repository upgrade in place: the add-on slug,
configuration, and persistent sessions stay the same. After the first release,
refresh the Add-on Store and open the add-on's page to install the update.
Enable automatic updates there if you want Home Assistant to install future
releases automatically. If you installed a local copy under `/addons` instead
of using this repository, install the repository version to receive its updates.

The `unstable` container tag remains available for development; Home Assistant
repository installations use numbered releases.

### Configure

1. Set `openai_api_key` in the add-on configuration (get one from [OpenAI Platform](https://platform.openai.com/api-keys)).
2. Optionally set a `model`, `review_approvals` (`ask` or `approve`), and `allow_internet_access` (`false` or `true`).
3. Start the add-on.
4. Click **Open Web UI** or find it in the sidebar.

### Usage

The add-on starts Codex with the workspace-write sandbox and access to your Home Assistant configuration. By default, Codex uses automatic approval review and commands have sandbox internet access. Set `review_approvals: ask` to review requests yourself and `allow_internet_access: false` to disable outbound command traffic. The automatic reviewer can reject requests.

- Working directory: `/config` (your HA config folder)
- When Codex exits, press Enter to restart or type `!exit` to quit
