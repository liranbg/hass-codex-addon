<!-- Managed by hass-codex-addon; put personal instructions in AGENTS.extend.md. -->
# Repository Guidelines

This file is refreshed by the add-on. Do not edit it directly.

## Optional User Instructions

Before starting work, read `AGENTS.extend.md` in the same directory as this file if it exists. Treat it as additional user instructions and context for this installation; it may refine or override the general environment assumptions below. If it is absent, continue with these guidelines. Put lasting user preferences in `AGENTS.extend.md`, which the add-on preserves across updates.

## Project Structure & Organization

This add-on works with a live Home Assistant configuration, normally under `/config`. If a different working directory is configured, inspect its contents before assuming the layout below.

- `configuration.yaml` defines integrations and includes; inspect it before adding configuration.
- `automations.yaml` and `scenes.yaml` contain lists; `scripts.yaml` contains a mapping keyed by script ID. Included files omit the parent `automation:`, `scene:`, or `script:` key.
- Where configured, `packages/` groups related integration settings, `templates/` supplies merged template lists, and `themes/` supplies merged theme mappings. Follow the actual include directives in `configuration.yaml`.
- `dashboards/` may contain YAML dashboards. Preserve the main Overview dashboard's configured mode; keep it in storage mode when required by `configuration.yaml`.
- `blueprints/` contains reusable definitions; `python_scripts/` contains Home Assistant Python scripts; `custom_components/` contains custom integrations; `www/` contains frontend assets. These folders may not all exist.

## Editing Style & Naming

Use two-space YAML indentation and no tabs. Preserve surrounding conventions and avoid unrelated reformatting. Use descriptive aliases, stable unique automation IDs, and lowercase snake_case script keys, such as `porch_light_on`.

Verify entity IDs and available actions in Developer Tools before using them. Choose automation/script `mode` deliberately (`single`, `restart`, `queued`, or `parallel`); make repeated actions safe where practical. Inspect existing definitions before adding overlapping behavior.

Follow the installed Home Assistant version's supported syntax. Consult official [automation](https://www.home-assistant.io/docs/automation/yaml/), [script](https://www.home-assistant.io/integrations/script/), and [include](https://www.home-assistant.io/docs/configuration/splitting_configuration/) documentation when uncertain.

## Validation & Development

Always run after configuration edits:

```sh
ha --no-progress --raw-json core check
```

This validates the on-disk Home Assistant configuration without applying changes. Report failures or unavailable validation explicitly; never claim an unchecked change passed.

For behavior changes, inspect templates in Developer Tools and verify automation traces and expected outcomes when safe. Configuration validation alone does not prove runtime behavior. After successful validation, use the relevant reload when applying an authorized change; restart only when needed. No application build is required for YAML edits.

## Commits & Pull Requests

Git history may be unavailable in this checkout. If contributing through Git, use concise imperative commit messages. Describe the behavior change, affected files, validation results, and reload requirements; include screenshots for dashboard changes and link relevant issues.

## Security & Runtime Files

Reference credentials with `!secret`; never print or commit secret values. Do not manually edit `.storage/`, databases, backups, or generated runtime folders such as `deps/` and `tts/`. Logs may contain sensitive information; redact before sharing. The recorder may use a secret-configured database URL, so do not assume local SQLite is the active database.
