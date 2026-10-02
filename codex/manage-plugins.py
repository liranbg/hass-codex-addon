"""Apply add-on plugin preferences through Codex's native plugin commands.

Codex owns Git downloads, marketplace validation, plugin caches, skill discovery,
and bundled MCP registration. This adapter chooses presets, refreshes moving
refs at startup, and records which plugins it installed so removing a preset
cannot uninstall plugins the user already had. It never runs an AI session.
"""

import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path


class PresetError(Exception):
    """A configuration or native CLI error safe to summarize in startup logs."""


def write_atomic(path: Path, content: str) -> None:
    """Replace a complete file while keeping existing permissions."""
    with tempfile.NamedTemporaryFile(
        mode="w", dir=path.parent, prefix=f".{path.name}.", delete=False
    ) as stream:
        temporary = Path(stream.name)
        try:
            if path.exists():
                temporary.chmod(path.stat().st_mode & 0o777)
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)


def codex(*args: str) -> dict:
    """Call the native CLI without a shell, login prompts, or credential output."""
    result = subprocess.run(
        ["codex", "plugin", *args, "--json"],
        check=True,
        capture_output=True,
        text=True,
        timeout=180,
        stdin=subprocess.DEVNULL,
        env=dict(os.environ, GIT_TERMINAL_PROMPT="0"),
    )
    response = json.loads(result.stdout)
    # Marketplace upgrades report per-source failures with a successful exit.
    if response.get("errors"):
        raise PresetError("marketplace refresh failed; keeping installed plugins")
    return response


def presets(entries: list[dict]) -> dict[str, dict]:
    """Group selected plugins by repository; a marketplace can have one ref."""
    if not isinstance(entries, list):
        raise PresetError("plugin_presets must be a list")
    groups = {}
    for entry in entries:
        if not isinstance(entry, dict):
            raise PresetError("each plugin preset must contain a repository")
        source = entry.get("repository", "")
        if not isinstance(source, str):
            raise PresetError("repository must be a GitHub URL")
        match = re.fullmatch(r"https://github\.com/([\w-]+)/([\w.-]+)/?", source)
        if not match or match[2].removesuffix(".git") in ("", ".", ".."):
            raise PresetError("repository must be https://github.com/owner/repository")
        source = f"https://github.com/{match[1]}/{match[2].removesuffix('.git')}.git"
        ref = entry.get("ref") or "HEAD"
        if (
            not isinstance(ref, str)
            or not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9._/-]*", ref)
            or ".." in ref
            or "//" in ref
            or ref.endswith(("/", ".", ".lock"))
        ):
            raise PresetError("ref must be a branch, tag, or full 40-character SHA")
        if re.fullmatch(r"[a-fA-F0-9]{7,39}", ref):
            raise PresetError("commit pins require the full 40-character SHA")
        if re.fullmatch(r"[a-fA-F0-9]{40}", ref):
            ref = ref.lower()
        plugin = entry.get("plugin") or ""
        if not isinstance(plugin, str) or (
            plugin and not re.fullmatch(r"[\w-]+", plugin)
        ):
            raise PresetError(
                "plugin must be a plugin name, without a marketplace suffix"
            )
        group = groups.setdefault(source, {"ref": ref, "plugins": set()})
        if group["ref"] != ref:
            raise PresetError("a repository cannot use multiple refs at the same time")
        group["plugins"].add(plugin)
    return groups


def set_ref(config: Path, marketplace: str, ref: str) -> str:
    """Change only the ref preference in Codex's supported marketplace config.

    The native CLI has no command for changing an existing marketplace's ref.
    Keep its other fields and every unrelated config section byte-for-byte.
    Return the prior config for rollback if the native upgrade fails.
    """
    previous = config.read_text()
    section = re.compile(
        rf"(^\[marketplaces\.(?:{re.escape(marketplace)}|{re.escape(json.dumps(marketplace))})\]\n)"
        r"(.*?)(?=^\[|\Z)",
        re.MULTILINE | re.DOTALL,
    )
    match = section.search(previous)
    if not match:
        raise PresetError("marketplace config not found; reopen /plugins to inspect it")
    body = match[2]
    setting = f"ref = {json.dumps(ref)}\n"
    if re.search(r"^ref\s*=", body, re.MULTILINE):
        body = re.sub(r"^ref\s*=.*\n?", lambda _: setting, body, flags=re.MULTILINE)
    else:
        body = setting + body
    updated = previous[: match.start(2)] + body + previous[match.end(2) :]
    if updated != previous:
        write_atomic(config, updated)
    return previous


def apply(entries: list[dict], home: Path) -> None:
    """Reconcile startup presets, preserving manual installs and offline caches."""
    groups = presets(entries)  # Reject malformed config before any removal.
    state_path = home / "addon-plugin-presets.json"
    state = (
        json.loads(state_path.read_text())
        if state_path.exists()
        else {"sources": {}, "plugins": {}}
    )
    if (
        not isinstance(state, dict)
        or not isinstance(state.get("sources"), dict)
        or not isinstance(state.get("plugins"), dict)
        or any(
            not isinstance(info, dict)
            or not isinstance(info.get("marketplace"), str)
            or not isinstance(info.get("ref"), str)
            for info in state["sources"].values()
        )
        or any(
            not isinstance(info, dict)
            or not isinstance(info.get("source"), str)
            or not isinstance(info.get("owned"), bool)
            for info in state["plugins"].values()
        )
    ):
        raise PresetError("preset ownership file is invalid; leaving plugins unchanged")
    if not groups and not state["plugins"]:
        return
    wanted = set()
    known = codex("marketplace", "list")["marketplaces"]
    marketplace_roots = {entry["name"]: Path(entry["root"]) for entry in known}
    marketplace_sources = {
        info["source"].rstrip("/").removesuffix(".git") + ".git": entry["name"]
        for entry in known
        if (info := entry.get("marketplaceSource", {})).get("sourceType") == "git"
    }

    # Save ownership immediately after each successful install, not only at the
    # end, so a later download failure cannot make us adopt a managed plugin.
    def save():
        write_atomic(state_path, json.dumps(state, indent=2) + "\n")

    for source, group in groups.items():
        saved = state["sources"].get(source, {})
        # Reuse a marketplace installed through /plugins, or left registered
        # after removing a preset, even if the newly selected ref differs.
        name = marketplace_sources.get(source)
        ref = group["ref"]
        # On failure, retain every previously installed plugin from this source.
        retained = {
            plugin
            for plugin, info in state["plugins"].items()
            if info["source"] == source
        }
        try:
            if name not in marketplace_roots or not marketplace_roots[name].exists():
                added = codex("marketplace", "add", source, "--ref", ref)
                name = added["marketplaceName"]
                saved = {"marketplace": name, "ref": ref}
                state["sources"][source] = saved
                save()
            else:
                config = home / "config.toml"
                previous = set_ref(config, name, ref)
                if saved.get("ref") != ref or config.read_text() != previous:
                    try:
                        codex("marketplace", "upgrade", name)
                    except Exception:
                        write_atomic(config, previous)
                        raise
                    state["sources"][source] = {"marketplace": name, "ref": ref}
                    save()
                elif not re.fullmatch(r"[a-f0-9]{40}", ref):
                    try:
                        codex("marketplace", "upgrade", name)
                    except (
                        PresetError,
                        OSError,
                        ValueError,
                        subprocess.SubprocessError,
                    ):
                        print(
                            f"WARNING: Could not refresh {name}; using its cached plugins.",
                            flush=True,
                        )

            listing = codex("list", "--marketplace", name, "--available")
            available = {
                plugin["name"]: plugin["pluginId"] for plugin in listing["available"]
            }
            installed = {plugin["pluginId"] for plugin in listing["installed"]}
            selected = group["plugins"]
            if "" in selected:
                if len(available) != 1:
                    choices = ", ".join(sorted(available)) or "none"
                    raise PresetError(
                        f"set plugin for marketplace {name}; available plugins: {choices}"
                    )
                selected = (selected - {""}) | set(available)
            for plugin in sorted(selected):
                if plugin not in available:
                    raise PresetError(
                        f"plugin {plugin} is not available in marketplace {name}"
                    )
                plugin_id = available[plugin]
                wanted.add(plugin_id)
                # Native add also refreshes installed bundles when their files
                # changed without a version bump, and registers bundled MCP.
                codex("add", plugin_id)
                state["plugins"].setdefault(
                    plugin_id, {"source": source, "owned": plugin_id not in installed}
                )
                save()
                print(f"Plugin preset ready: {plugin_id} ({ref}).", flush=True)
        except (PresetError, OSError, ValueError, subprocess.SubprocessError) as error:
            wanted.update(retained)
            detail = (
                str(error) if isinstance(error, PresetError) else type(error).__name__
            )
            print(
                f"WARNING: Could not apply plugin preset {source} ({ref}): {detail}. Check add-on configuration and repository access.",
                flush=True,
            )

    for plugin_id, info in list(state["plugins"].items()):
        if plugin_id in wanted:
            continue
        if info["owned"]:
            try:
                codex("remove", plugin_id)
            except (PresetError, OSError, ValueError, subprocess.SubprocessError):
                print(
                    f"WARNING: Could not remove preset {plugin_id}; retrying next startup.",
                    flush=True,
                )
                continue
        del state["plugins"][plugin_id]
    # Keep marketplaces registered for /plugins browsing and manual installs.
    state["sources"] = {
        source: info for source, info in state["sources"].items() if source in groups
    }
    save()


if __name__ == "__main__":
    try:
        options = Path(sys.argv[1])
        entries = (
            json.loads(options.read_text()).get("plugin_presets", [])
            if options.exists()
            else []
        )
        apply(entries, Path(os.environ["CODEX_HOME"]))
    except (PresetError, OSError, ValueError, subprocess.SubprocessError) as error:
        detail = str(error) if isinstance(error, PresetError) else type(error).__name__
        print(
            f"WARNING: Plugin presets skipped ({detail}); the terminal will still start.",
            flush=True,
        )
