"""Apply add-on plugin preferences through Codex's native plugin commands.

Codex owns Git downloads, marketplace validation, plugin caches, skill discovery,
and bundled MCP registration. This adapter chooses presets, refreshes moving
refs at startup, and records which plugins it installed so removing a preset
cannot uninstall plugins the user already had. It never runs an AI session.
"""

from __future__ import annotations

import json
import os
import re
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

STARTUP_TIMEOUT = 30


class PresetError(Exception):
    """A configuration or native CLI error safe to summarize in startup logs."""


class StartupTimeout(PresetError):
    """Stop reconciliation before cached plugins can be removed."""


class StartupCancelled(PresetError):
    """Interrupt native commands and roll back when the add-on is stopped."""


def cancel_startup(signum, frame):
    """Handle shutdown once; allow command cleanup and rollback to finish."""
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    raise StartupCancelled("preset setup cancelled by shutdown")


def command(args: list[str], deadline: float | None = None, limit: float = 180):
    """Bound command time and terminate descendants when a download stalls."""
    remaining = limit if deadline is None else min(limit, deadline - time.monotonic())
    message = "preset setup reached its startup deadline; retrying next startup"
    if remaining <= 0:
        raise StartupTimeout(message)
    with subprocess.Popen(
        args,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        stdin=subprocess.DEVNULL,
        start_new_session=True,
        env=dict(os.environ, GIT_TERMINAL_PROMPT="0"),
    ) as process:
        try:
            stdout, stderr = process.communicate(timeout=remaining)
        except (subprocess.TimeoutExpired, StartupCancelled) as error:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.communicate()
            if isinstance(error, StartupCancelled):
                raise
            if deadline is not None and remaining < limit:
                raise StartupTimeout(message) from None
            raise
        return subprocess.CompletedProcess(args, process.returncode, stdout, stderr)


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


def codex(*args: str, deadline: float | None = None) -> dict:
    """Call the native CLI without a shell, login prompts, or credential output."""
    # Put JSON before the positional separator so names beginning with '-' work.
    if args[0] in ("add", "remove"):
        argv = ["codex", "plugin", args[0], "--json", "--", *args[1:]]
    elif args[:2] == ("marketplace", "upgrade"):
        argv = ["codex", "plugin", *args[:2], "--json", "--", *args[2:]]
    else:
        argv = ["codex", "plugin", *args, "--json"]
    result = command(argv, deadline)
    result.check_returncode()
    response = json.loads(result.stdout)
    # Marketplace upgrades report per-source failures with a successful exit.
    if response.get("errors"):
        raise PresetError("marketplace refresh failed; keeping installed plugins")
    return response


def presets(entries: list[dict], deadline: float | None = None) -> dict[str, dict]:
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
            or ref.startswith("-")
            or "\0" in ref
            or command(
                ["git", "check-ref-format", "--allow-onelevel", ref], deadline, 5
            ).returncode
        ):
            raise PresetError("ref must be a branch, tag, or full 40-character SHA")
        if re.fullmatch(r"[a-fA-F0-9]{40}", ref):
            ref = ref.lower()
        plugin = entry.get("plugin") or ""
        if not isinstance(plugin, str) or (
            plugin and not re.fullmatch(r"[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)*", plugin)
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
    deadline = time.monotonic() + STARTUP_TIMEOUT
    groups = presets(entries, deadline)  # Reject malformed config before any removal.

    def native(*args):
        return codex(*args, deadline=deadline)

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
    lookup_failed = False
    try:
        known = native("marketplace", "list")["marketplaces"]
    except (StartupTimeout, StartupCancelled):
        raise
    except (PresetError, OSError, ValueError, subprocess.SubprocessError):
        # Native discovery validates every configured marketplace. One broken
        # unrelated manifest must not prevent scoped add/list operations.
        known = []
        lookup_failed = True
        print(
            "WARNING: Could not list all marketplaces; trying each preset independently.",
            flush=True,
        )
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
            refresh = True
            if name not in marketplace_roots or not marketplace_roots[name].exists():
                add_ref = saved.get("ref", ref) if lookup_failed else ref
                added = native("marketplace", "add", source, "--ref", add_ref)
                name = added["marketplaceName"]
                saved = {"marketplace": name, "ref": add_ref}
                state["sources"][source] = saved
                save()
                refresh = added.get("alreadyAdded", False) or add_ref != ref
            if refresh:
                config = home / "config.toml"
                previous = config.read_text()
                try:
                    set_ref(config, name, ref)
                    changed_ref = (
                        saved.get("ref") != ref or config.read_text() != previous
                    )
                    if changed_ref:
                        native("marketplace", "upgrade", name)
                except Exception:
                    write_atomic(config, previous)
                    raise
                if changed_ref:
                    state["sources"][source] = {"marketplace": name, "ref": ref}
                    save()
                elif not re.fullmatch(r"[a-f0-9]{40}", ref):
                    try:
                        native("marketplace", "upgrade", name)
                    except (StartupTimeout, StartupCancelled):
                        raise
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

            listing = native("list", f"--marketplace={name}", "--available")
            catalog = {
                plugin["name"]: plugin["pluginId"]
                for plugin in [*listing["installed"], *listing["available"]]
            }
            installed = {plugin["pluginId"] for plugin in listing["installed"]}
            selected = group["plugins"]
            if "" in selected:
                if len(catalog) != 1:
                    choices = ", ".join(sorted(catalog)) or "none"
                    raise PresetError(
                        f"set plugin for marketplace {name}; available plugins: {choices}"
                    )
                selected = (selected - {""}) | set(catalog)
            for plugin in sorted(selected):
                if plugin not in catalog:
                    raise PresetError(
                        f"plugin {plugin} is not available in marketplace {name}"
                    )
                plugin_id = catalog[plugin]
                wanted.add(plugin_id)
                # Native add also refreshes installed bundles when their files
                # changed without a version bump, and registers bundled MCP.
                native("add", plugin_id)
                state["plugins"].setdefault(
                    plugin_id, {"source": source, "owned": plugin_id not in installed}
                )
                save()
                print(f"Plugin preset ready: {plugin_id} ({ref}).", flush=True)
        except (StartupTimeout, StartupCancelled):
            raise
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
                native("remove", plugin_id)
            except (StartupTimeout, StartupCancelled):
                raise
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
    signal.signal(signal.SIGTERM, cancel_startup)
    signal.signal(signal.SIGINT, cancel_startup)
    try:
        options = Path(sys.argv[1])
        entries = (
            json.loads(options.read_text()).get("plugin_presets", [])
            if options.exists()
            else []
        )
        apply(entries, Path(os.environ["CODEX_HOME"]))
    except StartupCancelled:
        print("Plugin preset setup stopped.", flush=True)
    except (PresetError, OSError, ValueError, subprocess.SubprocessError) as error:
        detail = str(error) if isinstance(error, PresetError) else type(error).__name__
        print(
            f"WARNING: Plugin presets skipped ({detail}); the terminal will still start.",
            flush=True,
        )
