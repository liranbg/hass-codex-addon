"""Run real Codex plugin lifecycle checks in a disposable add-on container."""

import json
import os
import subprocess
from pathlib import Path

HOME = Path("/data/.codex")
REPO = Path("/fixture")
URL = "https://github.com/example/presets"
os.environ["CODEX_HOME"] = str(HOME)


def command(*args):
    return subprocess.check_output(args, text=True, stderr=subprocess.PIPE).strip()


def native(*args):
    return json.loads(command("codex", *args, "--json"))


def commit():
    command("git", "-C", str(REPO), "add", ".")
    command(
        "git",
        "-C",
        str(REPO),
        "-c",
        "user.name=Preset",
        "-c",
        "user.email=preset@example.invalid",
        "commit",
        "-m",
        "fixture",
    )
    return command("git", "-C", str(REPO), "rev-parse", "HEAD")


def start(entries):
    options = dict(
        openai_api_key="",
        model="",
        font_size=18,
        resume_last_session=False,
        working_directory="/config",
        review_approvals="approve",
        allow_internet_access=True,
        plugin_presets=entries,
    )
    Path("/data/options.json").write_text(json.dumps(options))
    output = command(
        "bash",
        "-ec",
        "source /usr/lib/bashio/bashio.sh; bashio::addon.config() { cat /data/options.json; }; source /run.sh",
    )
    assert "TERMINAL_READY" in output, output
    return output


Path("/data").mkdir(exist_ok=True)
(REPO / ".agents/plugins").mkdir(parents=True)
(REPO / ".agents/plugins/marketplace.json").write_text(
    json.dumps(
        dict(
            name="fixture",
            plugins=[
                dict(name=name, source=dict(source="local", path=f"./plugins/{name}"))
                for name in ("sample", "manual")
            ],
        )
    )
)
for name in ("sample", "manual"):
    folder = REPO / "plugins" / name
    (folder / ".codex-plugin").mkdir(parents=True)
    (folder / "skills/example").mkdir(parents=True)
    (folder / ".codex-plugin/plugin.json").write_text(
        json.dumps(
            dict(
                name=name, version="1.0.0", skills="./skills/", mcpServers="./.mcp.json"
            )
        )
    )
    (folder / ".mcp.json").write_text(
        json.dumps(
            dict(
                mcpServers={name: dict(type="http", url="https://example.invalid/mcp")}
            )
        )
    )
    (folder / "skills/example/SKILL.md").write_text(
        f"---\nname: {name}-fixture\ndescription: A native plugin fixture.\n---\nfirst revision\n"
    )
command("git", "-C", str(REPO), "init", "-b", "main")
first = commit()

# Redirect only GitHub downloads to the local fixture. Codex performs real Git
# cloning/upgrades, marketplace registration, plugin installation, and MCP setup.
bin_dir = Path("/tmp/test-bin")
bin_dir.mkdir()
(bin_dir / "git").write_text("""#!/usr/bin/env bash
printf '%s\\n' "$*" >> /data/git-calls.log
args=()
for arg in "$@"; do
  case "$arg" in
    https://github.com/example/presets*) args+=(file:///fixture) ;;
    *) args+=("$arg") ;;
  esac
done
exec /usr/bin/git "${args[@]}"
""")
(bin_dir / "ttyd").write_text("#!/bin/sh\necho TERMINAL_READY\n")
for path in bin_dir.iterdir():
    path.chmod(0o755)
os.environ["PATH"] = str(bin_dir) + ":" + os.environ["PATH"]
entry = dict(repository=URL, ref="main", plugin="sample")
start([entry])
installed = native("plugin", "list")["installed"]
assert [p["pluginId"] for p in installed] == ["sample@fixture"], installed
bundle = native("plugin", "add", "sample@fixture")
skill = Path(bundle["installedPath"]) / "skills/example/SKILL.md"
assert "first revision" in skill.read_text()
assert any(server["name"] == "sample" for server in native("mcp", "list"))
print("PASS: startup installs the selected native plugin and bundled MCP definition")

# Verify the native app-server discovers plugin skills before any AI login.
p = subprocess.Popen(
    ["codex", "--no-daemon", "app-server"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.DEVNULL,
    text=True,
)


def request(message):
    p.stdin.write(json.dumps(message) + "\n")
    p.stdin.flush()
    while True:
        line = p.stdout.readline()
        assert line, "app-server exited before responding"
        result = json.loads(line)
        if result.get("id") == message["id"]:
            assert "error" not in result, result
            return result["result"]


try:
    request(
        dict(
            id=1,
            method="initialize",
            params=dict(clientInfo=dict(name="preset-test", version="1.0")),
        )
    )
    result = request(
        dict(
            id=2, method="skills/list", params=dict(cwds=["/config"], forceReload=True)
        )
    )
    found = [
        s
        for row in result["data"]
        for s in row["skills"]
        if s.get("pluginId") == "sample@fixture"
    ]
    assert len(found) == 1 and found[0]["enabled"], result
finally:
    p.terminate()
    p.wait(timeout=10)
print("PASS: Codex discovers the installed plugin skill")

native("plugin", "add", "manual@fixture")
command("codex", "mcp", "add", "personal", "--url", "https://example.invalid/personal")
(REPO / "plugins/sample/skills/example/SKILL.md").write_text(
    "---\nname: sample-fixture\ndescription: A native plugin fixture.\n---\nsecond revision\n"
)
commit()
start([entry])
assert "second revision" in skill.read_text()
print("PASS: restart refreshes branch content even without a plugin version bump")

pin = dict(entry, ref=first)
start([pin])
assert "first revision" in skill.read_text()
Path("/data/git-calls.log").write_text("")
start([pin])
calls = Path("/data/git-calls.log").read_text()
assert "clone" not in calls and "ls-remote" not in calls, calls
assert "first revision" in skill.read_text()
print(
    "PASS: switching to a full commit pin works and restarts require no Git downloads"
)

before = (HOME / "config.toml").read_text()
output = start([dict(entry, ref="missing-branch")])
assert "WARNING:" in output
assert (HOME / "config.toml").read_text() == before
assert "first revision" in skill.read_text()
print("PASS: failed ref changes keep the previous config and plugin copy")

start([])
assert [p["pluginId"] for p in native("plugin", "list")["installed"]] == [
    "manual@fixture"
]
servers = [server["name"] for server in native("mcp", "list")]
assert "personal" in servers and "sample" not in servers, servers
assert native("plugin", "marketplace", "list")["marketplaces"]
print(
    "PASS: removing presets preserves manual plugins, MCP connections, and marketplaces"
)

start([entry])
assert "second revision" in skill.read_text()
assert sorted(p["pluginId"] for p in native("plugin", "list")["installed"]) == [
    "manual@fixture",
    "sample@fixture",
]
print("PASS: re-adding a preset reuses its marketplace with the newly selected ref")
