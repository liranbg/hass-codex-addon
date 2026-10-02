## OpenAI Codex (Terminal)

This add-on runs the **OpenAI Codex CLI** inside a **web-based terminal** exposed via **Home Assistant Ingress**.

Add-on format follows Home Assistant's developer docs: [Developing an add-on](https://developers.home-assistant.io/docs/add-ons/).

### Configuration

- **openai_api_key** (required): Your OpenAI API key from [OpenAI Platform](https://platform.openai.com/api-keys).
- **model** (optional): Override the default model (e.g., `gpt-5.1-codex-mini`, `gpt-5.2-codex`).
- **resume_last_session** (optional, default `false`): Resume your most recent Codex session on startup.
- **font_size** (optional, default `18`): Terminal font size (range: 10–40).
- **working_directory** (optional, default `/config`): The directory Codex operates in.
- **review_approvals** (optional, default `approve`): `ask` shows approval requests to you. `approve` uses Codex's automatic reviewer for eligible requests; it can approve or reject them rather than approving everything.
- **allow_internet_access** (optional, default `true`): Allow outbound network access for commands inside the Codex sandbox. This setting does not disable the OpenAI connection needed to run Codex.

For automatic review with internet access, set:

```yaml
review_approvals: approve
allow_internet_access: true
```

Both review modes use `approval_policy = "on-request"` and the **`workspace-write` sandbox**. The add-on explicitly passes these settings to each new or resumed Codex session. Restart the add-on after changing the options.

See the [OpenAI sandbox documentation](https://learn.chatgpt.com/docs/sandboxing) for approval and network behavior.

### Usage

1. Configure your OpenAI API key in the add-on settings.
2. Start the add-on.
3. Open the add-on UI (via Ingress in the sidebar).

The terminal automatically:

- Logs in using your API key
- Refreshes the managed `AGENTS.md` in the working directory from the bundled template, preserving personal instructions separately
- Starts Codex with the **workspace-write sandbox** and your approval review and internet access settings
- Restarts the session when Codex exits (type `!exit` to quit)

### Examples

Here are some things you can ask Codex to do:

- **Create an automation:** "Create an automation that turns off all lights at midnight."
- **Debug a sensor:** "My `sensor.temperature` hasn't updated in 2 hours. Help me debug why."
- **Add an integration:** "Set up the MQTT integration and create a binary sensor for `zigbee2mqtt/door_sensor`."
- **Clean up config:** "Find and remove any unused entities or helpers from my configuration."
- **Create a scene:** "Create a 'Movie Night' scene that dims the living room lights to 20% and turns on the TV."

### AGENTS.md Template

Whenever you open the terminal, the add-on refreshes `AGENTS.md` in your working directory from the bundled `AGENTS.tmpl.md`. This file provides Codex with context about the Home Assistant environment, including:

- Key files and folders (`configuration.yaml`, `automations.yaml`, etc.)
- Common tasks (adding automations, scenes, integrations)
- Validation commands and safety guidelines

Put your own instructions in **`AGENTS.extend.md`** beside `AGENTS.md` (by default, `/config/AGENTS.extend.md`). This file is optional and is never overwritten by the add-on. The managed template tells Codex to read it before starting work and use it as additional instructions and installation context. Edit the extension instead of `AGENTS.md`, because changes to the managed file are replaced when you reopen the terminal.

On the first upgrade to managed instructions, an existing `AGENTS.md` is saved as `AGENTS.md.backup.XXXXXX`. If no extension exists, its contents are also copied to `AGENTS.extend.md`. Review this migrated extension and remove old bundled defaults, keeping your personal instructions. If an extension already exists, it is preserved; the terminal shows the backup path so you can merge any personal instructions yourself.

To ship new defaults to an existing installation, edit `codex/AGENTS.tmpl.md` and publish an add-on release following `DEVELOPMENT.md`. Install that update in Home Assistant and reopen the terminal to apply the new template. An already-running Codex session must be restarted to load the updated guidance. A restart of the old add-on image cannot pick up repository changes.

Codex's native `AGENTS.override.md` replaces `AGENTS.md` in the same directory. If you use that override, include your own instruction to read the extension. Symlinked or non-file `AGENTS.md` paths are rejected to avoid replacing user-managed links.

### Session Resume

- When **resume_last_session** is enabled, Codex picks up where you left off instead of starting a new session.
- Session data is stored persistently across container restarts in the add-on's data directory.
- Sessions may contain conversation history including prompts and generated code. Keep this in mind if you share backups of your Home Assistant instance.

### API Usage & Costs

- Codex sends requests to the OpenAI API while working. Depending on the model and task complexity, this can consume significant API credits.
- Monitor your usage at [OpenAI Usage](https://platform.openai.com/usage).
- Consider using a less expensive model (e.g., `gpt-5.1-codex-mini`) for routine tasks.

### Notes / Security

- The terminal is accessible through Home Assistant Ingress (Supervisor handles authentication).
- The API key is stored in the add-on configuration and exported to the terminal session.
- The **workspace-write sandbox** allows Codex to execute commands and create, modify, and delete files in your working directory. Eligible requests to go beyond the sandbox are reviewed by you (`ask`) or the automatic reviewer (`approve`). Use with caution and review changes before restarting Home Assistant.
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

**"failed to read start time for pid-managed app server"**
- The background Codex server failed during process tracking. The add-on launches new and resumed sessions with `--no-daemon` to avoid this startup path.
- Update to an add-on release containing this fix, or rebuild from the updated source, then reopen the terminal.

**Changes not taking effect after editing configuration**
- You must restart the add-on after changing any configuration option.

**Session resume not working**
- Ensure `resume_last_session` is set to `true` in the add-on configuration.
- If there is no previous session, Codex will start a new one automatically.
