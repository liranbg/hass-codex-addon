## OpenAI Codex (Terminal)

This add-on runs the **OpenAI Codex CLI** inside a **web-based terminal** exposed via **Home Assistant Ingress**.

Add-on format follows Home Assistant's developer docs: [Developing an add-on](https://developers.home-assistant.io/docs/add-ons/).

### Configuration

- **openai_api_key** (required): Your OpenAI API key from [OpenAI Platform](https://platform.openai.com/api-keys).
- **model** (optional): Override the default model (e.g., `gpt-5.1-codex-mini`, `gpt-5.2-codex`).
- **resume_last_session** (optional, default `false`): Resume your most recent Codex session on startup.
- **font_size** (optional, default `18`): Terminal font size (range: 10–40).
- **working_directory** (optional, default `/config`): The directory Codex operates in.

### Usage

1. Configure your OpenAI API key in the add-on settings.
2. Start the add-on.
3. Open the add-on UI (via Ingress in the sidebar).

The terminal automatically:

- Logs in using your API key
- Creates an `AGENTS.md` file in the working directory if one doesn't exist (provides Home Assistant context to Codex)
- Starts Codex in **full-auto mode**
- Restarts the session when Codex exits (type `!exit` to quit)

### Examples

Here are some things you can ask Codex to do:

- **Create an automation:** "Create an automation that turns off all lights at midnight."
- **Debug a sensor:** "My `sensor.temperature` hasn't updated in 2 hours. Help me debug why."
- **Add an integration:** "Set up the MQTT integration and create a binary sensor for `zigbee2mqtt/door_sensor`."
- **Clean up config:** "Find and remove any unused entities or helpers from my configuration."
- **Create a scene:** "Create a 'Movie Night' scene that dims the living room lights to 20% and turns on the TV."

### AGENTS.md Template

On first run, the add-on copies a bundled `AGENTS.tmpl.md` template to `AGENTS.md` in your working directory. This file provides Codex with context about the Home Assistant environment, including:

- Key files and folders (`configuration.yaml`, `automations.yaml`, etc.)
- Common tasks (adding automations, scenes, integrations)
- Validation commands and safety guidelines

You can customize this file to better suit your setup. It won't be overwritten if it already exists.

### Session Resume

- When **resume_last_session** is enabled, Codex picks up where you left off instead of starting a new session.
- Session data is stored persistently across container restarts in the add-on's data directory.
- Sessions may contain conversation history including prompts and generated code. Keep this in mind if you share backups of your Home Assistant instance.

### API Usage & Costs

- **Full-auto mode** sends requests to the OpenAI API automatically. Depending on the model and task complexity, this can consume significant API credits.
- Monitor your usage at [OpenAI Usage](https://platform.openai.com/usage).
- Consider using a less expensive model (e.g., `gpt-5.1-codex-mini`) for routine tasks.

### Notes / Security

- The terminal is accessible through Home Assistant Ingress (Supervisor handles authentication).
- The API key is stored in the add-on configuration and exported to the terminal session.
- **Full-auto mode** allows Codex to execute commands automatically — it can create, modify, and delete files in your `/config` directory. Use with caution and review changes before restarting Home Assistant.
- The working directory defaults to `/config`, which is your Home Assistant configuration folder.

### Troubleshooting

**Blank screen or terminal not loading**
- Check the add-on logs for errors (Settings > Add-ons > OpenAI Codex > Log).
- Restart the add-on. If the problem persists, try rebuilding the image.

**"Login failed" or authentication errors**
- Verify your API key is correct and active at [OpenAI Platform](https://platform.openai.com/api-keys).
- Ensure the key starts with `sk-`. The add-on will warn you on startup if the format looks wrong.

**"Codex CLI not found" error**
- The add-on image may be corrupted. Rebuild the add-on from the Home Assistant settings.

**Codex exits immediately or crashes**
- Check if your API key has billing/quota issues at [OpenAI Usage](https://platform.openai.com/usage).
- Try a different model (e.g., `gpt-5.1-codex-mini`) in the add-on configuration.

**Changes not taking effect after editing configuration**
- You must restart the add-on after changing any configuration option.

**Session resume not working**
- Ensure `resume_last_session` is set to `true` in the add-on configuration.
- If there is no previous session, Codex will start a new one automatically.
