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
- **plugin_presets** (optional, default `[]`): Plugins to install from public GitHub marketplaces before Codex starts. Each entry has a `repository`, optional `ref`, and optional `plugin`. See Plugin presets below.
- **allow_internet_access** (optional, default `true`): Allow outbound network access for commands inside the Codex sandbox. This setting does not disable the OpenAI connection needed to run Codex.

For automatic review with internet access, set:

```yaml
review_approvals: approve
allow_internet_access: true
```

Both review modes use `approval_policy = "on-request"` and the **`workspace-write` sandbox**. The add-on explicitly passes these settings to each new or resumed Codex session. Restart the add-on after changing the options.

See the [OpenAI sandbox documentation](https://learn.chatgpt.com/docs/sandboxing) for approval and network behavior.

### Plugin presets

Add repositories in the add-on configuration, then restart the add-on:

```yaml
plugin_presets:
  - repository: https://github.com/homeassistant-ai/skills
```

Open the terminal and use `/plugins` to inspect the installed plugin and `/skills` to see its skills. The [Home Assistant marketplace](https://github.com/homeassistant-ai/skills) contains a single plugin, so its name is selected automatically. If a marketplace contains several plugins, set `plugin` to the name you want; the add-on logs the available names when it cannot select one. Repeat an entry with another plugin name to select several from the same marketplace.

Codex's native plugin manager clones the marketplace, installs the selected plugins, discovers their skills, and registers bundled MCP server definitions. The add-on only applies your preset preferences at startup. No OpenAI login or model request is needed for installation. Codex stores marketplaces, plugins, settings, and credentials under persistent `/data/.codex`; restarting or upgrading the add-on preserves them. See [Codex plugins](https://learn.chatgpt.com/docs/plugins).

Presets require a Codex-compatible marketplace manifest, such as `.agents/plugins/marketplace.json` or the supported `.claude-plugin/marketplace.json` layout used by the Home Assistant repository. A plain repository containing only `SKILL.md` files is not a plugin marketplace; install those skills separately through Codex's skill installer.

#### References and updates

Set `ref` to a branch, tag, or full commit SHA. Omit it to follow the repository's default branch:

```yaml
plugin_presets:
  - repository: https://github.com/homeassistant-ai/skills
    ref: main
    plugin: home-assistant-skills
```

For a development branch, use a value such as `ref: feature/ha`. For a tag, use `ref: v1.0.0`. For a commit pin, copy the full 40-character SHA from GitHub into `ref`; abbreviated hashes are rejected. All plugins from the same marketplace share one reference, so do not configure that repository at multiple refs.

| Configuration | On each add-on restart |
| --- | --- |
| No `ref` (or `HEAD`) | Check the latest default-branch revision |
| Branch | Check the latest revision of that branch |
| Tag | Check the revision the tag currently points to; a moved tag is updated |
| Full commit SHA | Keep the pinned marketplace revision; skip marketplace refresh after installation |

On each add-on start, the adapter asks Codex to refresh moving references and reinstall the selected plugin bundles when necessary, including content changes without a plugin version bump. Codex validates a staged marketplace before replacing its cached copy. A failed refresh logs a warning and retains installed plugins; the terminal still opens and the refresh retries on the next start. Changing a configured reference also uses the native updater; if it fails, the previous reference setting is restored.

Restart the **add-on** to apply preset changes and fetch updates. Opening the terminal or restarting only a Codex session does not run this startup refresh. To change a pin, replace its SHA and restart the add-on. Plugins can also be managed through Codex's `/plugins` interface. Preset configuration is reapplied at the next add-on start, so remove a preset from configuration if you want to uninstall it permanently.

To refresh the Home Assistant plugin from an existing Codex session, ask Codex to refresh its marketplace and reinstall the plugin, or run these native commands from a shell:

```bash
codex plugin marketplace upgrade home-assistant-skills
codex plugin add home-assistant-skills@home-assistant-skills
```

The first command updates the marketplace at its configured ref; the second refreshes the installed bundle. A pinned ref stays pinned.

A commit pin fixes the marketplace revision. If a marketplace points to plugins in separate repositories, their own source references control their versions. MCP executables, package dependencies, and remote services also have their own update lifecycle.

Removing a preset uninstalls a plugin only if the add-on originally installed it. A plugin that was already installed manually is kept. Registered marketplaces remain available in `/plugins`, and unrelated plugins, standalone skills, and standalone MCP connections are preserved.

Downloads and moving-reference refreshes require internet access regardless of `allow_internet_access`, which controls commands inside Codex sessions. Cached plugin content remains available offline. Only add repositories whose instructions and tools you trust. Presets accept public GitHub repository URLs (with an optional `.git` suffix); use `ref` instead of a GitHub `/tree/…` or `/commit/…` page URL.

#### MCP connections

Installing a plugin registers any MCP server definitions it bundles. A server may still require a URL, credentials, OAuth sign-in, or runtime dependencies. Open `/mcp` to inspect connection status and complete setup; installation alone does not grant access to an external service. The add-on does not invent credentials or run repository setup scripts.

For a standalone MCP server, ask Codex to configure it or use the native `codex mcp add` command. Those settings persist independently of presets. MCP OAuth credentials created inside the interactive Codex session are saved to files under persistent `CODEX_HOME`, so ordinary restarts retain the login. Providers can still require reauthentication when credentials expire or are revoked. See [Codex MCP setup](https://learn.chatgpt.com/docs/extend/mcp).

### Usage

1. Leave `openai_api_key` empty for ChatGPT sign-in, or configure an API key in the add-on settings.
2. Start the add-on.
3. Open the add-on UI (via Ingress in the sidebar).

The terminal automatically:

- Reuses your saved Codex login, or logs in using your configured API key if no saved login exists. With neither, Codex prompts you to choose a sign-in method.
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
