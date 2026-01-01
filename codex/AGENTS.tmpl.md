# Home Assistant Config Playbook (for Agents)

Purpose: quick orientation for working inside the Home Assistant container at `/config` so we can safely inspect, extend, and debug automations, scripts, and related settings.

## Environment Notes

- Working dir: `/config`; main entry point `configuration.yaml` uses `default_config` and includes `automations.yaml`, `scripts.yaml`, `scenes.yaml`, and themes via `frontend`.
- Sandbox: reading files may require escalated permission (Landlock errors); rerun commands with `require_escalated` when blocked.
- Sensitive data: `secrets.yaml` holds credentials; never print, use or commit its contents.

## Key Files and Folders

- `configuration.yaml`: root config; add new integrations, includes, and globals here.
- `automations.yaml`: list of automations (currently `[]`). Append new dict items here.
- `scripts.yaml`: Home Assistant scripts (currently empty).
- `scenes.yaml`: scenes definitions (currently empty).
- `blueprints/`: stock blueprints: `automation/homeassistant/*.yaml`, `script/homeassistant/*.yaml`.
- `themes/`: referenced by `frontend` (folder may be empty).
- `home-assistant_v2.db*`: runtime database; do not edit. `home-assistant.log*` contains logs.
- `deps/`, `tts/`: runtime folders; avoid manual edits.

## Common Tasks

- **Add automation**: append to `automations.yaml`.
  ```yaml
  - alias: Turn on porch light at sunset
    trigger:
  … +22 lines
        target:
          entity_id: scene.relax
  ```
- **Add scene**: place scenes in `scenes.yaml`.
  ```yaml
  - name: Relax
    entities:
      light.living_room:
        state: on
        brightness: 120
  ```
- **Add integration entries**: extend `configuration.yaml` or `!include` separate files when sections grow (e.g., `sensor: !include sensors.yaml`).
- **Use secrets**: reference with `!secret my_token` and store values in `secrets.yaml`.

## Validation & Reloading

- CLI: `ha --no-progress --raw-json core check`.
- YAML hygiene: use spaces (2 per indent), dash lists, and entity IDs from the UI.
- Always run the CLI check.

## Safety Checklist

- Never expose tokens from `secrets.yaml` or DB.
- Avoid touching `home-assistant_v2.db*`; use UI/history exports instead.
- Keep automations/scripts idempotent; set `mode` appropriately to avoid overlaps.
- If unsure about entity IDs or services, verify via UI Developer Tools → States/Services before writing YAML.
