#!/usr/bin/env python3
"""Manage the intended release separately from Home Assistant's published version."""

import argparse
import re
from pathlib import Path


IMAGE = "ghcr.io/liranbg/hass-codex-addon/{arch}"


def semver(value):
    if not re.fullmatch(r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)", value):
        raise ValueError(f"Expected a stable major.minor.patch version, got {value!r}")
    return tuple(map(int, value.split(".")))


def metadata(root):
    target = (root / "codex/VERSION").read_text().strip()
    semver(target)
    config = (root / "codex/config.yaml").read_text()
    match = re.search(r"^version: ([^\n]+)$", config, re.M)
    if not match:
        raise ValueError("Missing config.yaml version")
    published = match[1].strip('"\'')
    if published != "dev" and semver(target) < semver(published):
        raise ValueError("The release target cannot be older than the published version")
    changelog = (root / "codex/CHANGELOG.md").read_text()
    match = re.search(rf"^## {re.escape(target)}\n(.*?)(?=^## |\Z)", changelog, re.M | re.S)
    if not match or not match[1].strip():
        raise ValueError(f"Missing changelog entry for {target}")
    return target, published, config, match[1].strip() + "\n"


def update(root, latest):
    semver(latest)
    target, published, _, _ = metadata(root)
    # Do not stack another release on an unpublished target.
    if target != published:
        return False
    dockerfile = root / "codex/Dockerfile"
    text = dockerfile.read_text()
    pins = re.findall(r"@openai/codex@([0-9]+\.[0-9]+\.[0-9]+)(?=\s|$)", text)
    if len(pins) != 1:
        raise ValueError("Expected exactly one pinned Codex CLI version")
    if semver(latest) <= semver(pins[0]):
        return False
    major, minor, patch = semver(target)
    version = f"{major}.{minor}.{patch + 1}"
    dockerfile.write_text(text.replace(f"@openai/codex@{pins[0]}", f"@openai/codex@{latest}"))
    (root / "codex/VERSION").write_text(version + "\n")
    changelog = root / "codex/CHANGELOG.md"
    text = changelog.read_text()
    entry = f"## {version}\n\n- Update Codex CLI from {pins[0]} to {latest}.\n\n"
    changelog.write_text(text.replace("# Changelog\n\n", "# Changelog\n\n" + entry, 1))
    return True


def promote(root):
    target, _, config, _ = metadata(root)
    config = re.sub(r"^version: [^\n]+$", f'version: "{target}"', config, flags=re.M)
    if re.search(r"^image:", config, re.M):
        config = re.sub(r"^image: [^\n]+$", f'image: "{IMAGE}"', config, flags=re.M)
    else:
        config = config.replace(f'version: "{target}"\n', f'version: "{target}"\nimage: "{IMAGE}"\n', 1)
    (root / "codex/config.yaml").write_text(config)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["check", "update", "promote", "notes"])
    parser.add_argument("--codex-version")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    if args.command == "update":
        if not args.codex_version:
            parser.error("update requires --codex-version")
        print(f"changed={str(update(root, args.codex_version)).lower()}")
    elif args.command == "promote":
        promote(root)
    else:
        target, published, _, notes = metadata(root)
        if args.command == "notes":
            print(notes, end="")
        else:
            print(f"version={target}")
            print(f"pending={str(target != published).lower()}")


if __name__ == "__main__":
    main()
