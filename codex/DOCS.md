## OpenAI Codex (Terminal)

This add-on runs the **OpenAI Codex CLI** inside a **web-based terminal** exposed via **Home Assistant Ingress**.

Add-on format follows Home Assistant's developer docs: [Developing an add-on](https://developers.home-assistant.io/docs/add-ons/).

### Configuration

- **openai_api_key** (optional): Your OpenAI API key from [OpenAI Platform](https://platform.openai.com/api-keys), used when no saved login exists. Leave empty to sign in with ChatGPT.
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

1. Leave `openai_api_key` empty for ChatGPT sign-in, or configure an API key in the add-on settings.
2. Start the add-on.
3. Open the add-on UI (via Ingress in the sidebar).

The terminal automatically:

- Reuses your saved Codex login, or logs in using your configured API key if no saved login exists. With neither, Codex prompts you to choose a sign-in method.
- Creates an `AGENTS.md` file in the working directory if one doesn't exist (provides Home Assistant context to Codex)
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

On first run, the add-on copies a bundled `AGENTS.tmpl.md` template to `AGENTS.md` in your working directory. This file provides Codex with context about the Home Assistant environment, including:

- Key files and folders (`configuration.yaml`, `automations.yaml`, etc.)
- Common tasks (adding automations, scenes, integrations)
- Validation commands and safety guidelines

You can customize this file to better suit your setup. It won't be overwritten if it already exists.

### Session Resume

- When **resume_last_session** is enabled, Codex picks up where you left off instead of starting a new session.
- Session data is stored persistently across container restarts in the add-on's data directory.
- Sessions may contain conversation history including prompts and generated code. Keep this in mind if you share backups of your Home Assistant instance.

### Persistent Authentication

Codex stores its credentials and configuration under `/data/.codex` (`CODEX_HOME`), in the add-on's persistent data directory. Your last login method (ChatGPT or API key) survives add-on restarts and updates. Existing session history remains under `/data/.codex-sessions`.

After installing this fix, sign in once if the previous container's credentials were already lost. For ChatGPT sign-in in Home Assistant, choose **Sign in with Device Code** in the login screen. Device code login must be enabled in your ChatGPT account or workspace settings. See [OpenAI authentication documentation](https://learn.chatgpt.com/docs/auth).

To switch accounts or login methods, use `/logout` in Codex, then sign in again. To switch to a different configured API key, log out and reopen the add-on terminal. A configured key does not overwrite an existing saved login.

Persistence does not prevent reauthentication if credentials are revoked or expire beyond recovery. Add-on backups include credentials; treat them as sensitive. Uninstalling the add-on or deleting its data removes the saved login.

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
