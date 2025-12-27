## OpenAI Codex (Terminal)

This add-on runs the **OpenAI Codex CLI** inside a **web-based terminal** exposed via **Home Assistant Ingress**.

Add-on format follows Home Assistant's developer docs: [Developing an add-on](https://developers.home-assistant.io/docs/add-ons/).

### Configuration

- **openai_api_key** (required): Your OpenAI API key from [OpenAI Platform](https://platform.openai.com/api-keys).
- **model** (optional): Override the default model (e.g., `gpt-4o`, `o3`).

### Usage

1. Configure your OpenAI API key in the add-on settings.
2. Start the add-on.
3. Open the add-on UI (via Ingress in the sidebar).

The terminal automatically:

- Logs in using your API key
- Starts Codex in **full-auto mode** (working directory: `/config`)
- Restarts the session when Codex exits (type `exit` to quit)

### Notes / Security

- The terminal is accessible through Home Assistant Ingress (Supervisor handles authentication).
- The API key is stored in the add-on configuration and exported to the terminal session.
- **Full-auto mode** allows Codex to execute commands automatically. Use with caution.
- The working directory `/config` is your Home Assistant configuration folder.
