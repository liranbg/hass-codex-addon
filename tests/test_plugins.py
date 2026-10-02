"""Check preset selection, ownership, and update policy around the native CLI."""

import importlib.util
import json
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "manage_plugins", ROOT / "codex/manage-plugins.py"
)
plugins = importlib.util.module_from_spec(spec)
spec.loader.exec_module(plugins)
URL = "https://github.com/example/plugins"
SHA = "a" * 40


class PluginTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.root = self.home / "marketplace"
        self.root.mkdir()
        self.marketplace = False
        self.available = ["example"]
        self.installed = set()
        self.calls = []
        self.config = self.home / "config.toml"
        self.config.write_text(
            'model = "custom"\n\n[marketplaces.fixture]\nsource_type = "git"\nsource = "https://github.com/example/plugins.git"\nref = "main"\n\n[mcp_servers.personal]\nurl = "https://example.invalid/mcp"\n'
        )
        self.mock = patch.object(plugins, "codex", side_effect=self.native)
        self.mock.start()
        self.addCleanup(self.mock.stop)

    def native(self, *args, **kwargs):
        self.calls.append(args)
        if args == ("marketplace", "list"):
            return {
                "marketplaces": [
                    {
                        "name": "fixture",
                        "root": str(self.root),
                        "marketplaceSource": {"sourceType": "git", "source": URL},
                    }
                ]
                if self.marketplace
                else []
            }
        if args[:2] == ("marketplace", "add"):
            already = self.marketplace
            self.marketplace = True
            self.config.write_text(
                self.config.read_text().replace('ref = "main"', f'ref = "{args[-1]}"')
            )
            return {"marketplaceName": "fixture", "alreadyAdded": already}
        if args[:2] == ("marketplace", "upgrade"):
            return {"errors": []}
        if args[:1] == ("list",):
            return {
                "installed": [
                    {"name": name.rsplit("@", 1)[0], "pluginId": name}
                    for name in self.installed
                    if name.endswith("@fixture")
                ],
                "available": [
                    {"name": name, "pluginId": name + "@fixture"}
                    for name in self.available
                    if name + "@fixture" not in self.installed
                ],
            }
        if args[:1] == ("add",):
            self.installed.add(args[1])
            return {"pluginId": args[1]}
        if args[:1] == ("remove",):
            self.installed.discard(args[1])
            return {}
        raise AssertionError(args)

    def entry(self, **kwargs):
        return dict(repository=URL, ref="main", **kwargs)

    def state(self):
        return json.loads((self.home / "addon-plugin-presets.json").read_text())

    def test_single_plugin_autoselects_and_refreshes_on_restart(self):
        plugins.apply([self.entry()], self.home)
        self.assertEqual(self.installed, {"example@fixture"})
        self.assertIn(("marketplace", "add", URL + ".git", "--ref", "main"), self.calls)
        self.calls.clear()
        plugins.apply([self.entry()], self.home)
        self.assertIn(("marketplace", "upgrade", "fixture"), self.calls)
        self.assertIn(("add", "example@fixture"), self.calls)
        self.assertFalse(any(call[:2] == ("marketplace", "add") for call in self.calls))

    def test_commit_pins_skip_marketplace_refresh(self):
        entry = dict(repository=URL, ref=SHA)
        plugins.apply([entry], self.home)
        self.calls.clear()
        plugins.apply([entry], self.home)
        self.assertFalse(
            any(call[:2] == ("marketplace", "upgrade") for call in self.calls)
        )
        self.assertIn(("add", "example@fixture"), self.calls)

    def test_hexadecimal_names_are_moving_refs(self):
        for ref in ("deadbee", "deadbeef", "DEADBEEF", "a" * 39):
            with self.subTest(ref=ref):
                entry = dict(repository=URL, ref=ref)
                plugins.apply([entry], self.home)
                self.calls.clear()
                plugins.apply([entry], self.home)
                self.assertIn(("marketplace", "upgrade", "fixture"), self.calls)
                self.assertEqual(self.state()["sources"][URL + ".git"]["ref"], ref)
                self.assertEqual(self.installed, {"example@fixture"})

    def test_git_ref_grammar_accepts_punctuation_and_rejects_invalid_refs(self):
        for ref in ("release+candidate", "feature@beta", "rélease", "refs/tags/v1"):
            with self.subTest(ref=ref):
                groups = plugins.presets([dict(repository=URL, ref=ref)])
                self.assertEqual(groups[URL + ".git"]["ref"], ref)
        for ref in (
            ".hidden",
            "foo//bar",
            "name.lock",
            "foo@{bar",
            "-option",
            "a\0b",
            "@",
        ):
            with self.subTest(ref=ref), self.assertRaises(plugins.PresetError):
                plugins.presets([dict(repository=URL, ref=ref)])

    def test_multiple_plugins_need_explicit_selection(self):
        self.available = ["example", "another"]
        plugins.apply([self.entry()], self.home)
        self.assertEqual(self.installed, set())
        plugins.apply([self.entry(plugin="another")], self.home)
        self.assertEqual(self.installed, {"another@fixture"})

    def test_multiple_selected_plugins_share_one_marketplace(self):
        self.available = ["example", "another"]
        plugins.apply(
            [self.entry(plugin="example"), self.entry(plugin="another")], self.home
        )
        self.assertEqual(self.installed, {"example@fixture", "another@fixture"})
        self.assertEqual(
            sum(call[:2] == ("marketplace", "add") for call in self.calls), 1
        )

    def test_plugin_names_match_native_ascii_dotted_grammar(self):
        self.available = ["acme.tools", "-tools.v2"]
        for name in self.available:
            with self.subTest(name=name):
                plugins.apply([self.entry(plugin=name)], self.home)
                self.assertIn(name + "@fixture", self.installed)
        for name in (
            "café",
            ".tools",
            "tools.",
            "acme..tools",
            "../tools",
            "x@fixture",
        ):
            with self.subTest(name=name), self.assertRaises(plugins.PresetError):
                plugins.presets([self.entry(plugin=name)])

    def test_removing_one_preset_after_all_marketplace_plugins_are_installed(self):
        self.available = ["example", "another"]
        plugins.apply(
            [self.entry(plugin="example"), self.entry(plugin="another")], self.home
        )
        plugins.apply([self.entry(plugin="example")], self.home)
        self.assertEqual(self.installed, {"example@fixture"})

    def test_shutdown_restores_a_pending_ref_and_preserves_ownership(self):
        plugins.apply([self.entry()], self.home)
        before = self.config.read_text()
        ownership = (self.home / "addon-plugin-presets.json").read_text()

        def cancelled(*args, **kwargs):
            if args[:2] == ("marketplace", "upgrade"):
                raise plugins.StartupCancelled("shutdown")
            return self.native(*args)

        with (
            patch.object(plugins, "codex", side_effect=cancelled),
            self.assertRaises(plugins.StartupCancelled),
        ):
            plugins.apply([dict(repository=URL, ref=SHA)], self.home)
        self.assertEqual(self.config.read_text(), before)
        self.assertEqual(
            (self.home / "addon-plugin-presets.json").read_text(), ownership
        )

    def test_global_discovery_failure_uses_scoped_preset_operations(self):
        plugins.apply([self.entry()], self.home)
        self.available = ["example", "another"]

        def broken_discovery(*args, **kwargs):
            if args == ("marketplace", "list"):
                raise plugins.PresetError("unrelated marketplace is broken")
            return self.native(*args)

        with patch.object(plugins, "codex", side_effect=broken_discovery):
            plugins.apply(
                [self.entry(plugin="example"), self.entry(plugin="another")], self.home
            )
        self.assertEqual(self.installed, {"example@fixture", "another@fixture"})
        self.assertTrue(self.state()["plugins"]["another@fixture"]["owned"])

    def test_removal_only_uninstalls_owned_plugins(self):
        self.installed.add("personal@other")
        plugins.apply([self.entry()], self.home)
        plugins.apply([], self.home)
        self.assertEqual(self.installed, {"personal@other"})
        self.assertTrue(self.marketplace)

    def test_preexisting_plugin_is_preserved_after_removing_preset(self):
        self.marketplace = True
        self.installed.add("example@fixture")
        plugins.apply([self.entry()], self.home)
        self.assertFalse(self.state()["plugins"]["example@fixture"]["owned"])
        plugins.apply([], self.home)
        self.assertEqual(self.installed, {"example@fixture"})

    def test_readding_removed_preset_reuses_marketplace_with_new_ref(self):
        plugins.apply([self.entry()], self.home)
        plugins.apply([], self.home)
        self.calls.clear()
        plugins.apply([dict(repository=URL, ref=SHA)], self.home)
        self.assertIn(("marketplace", "upgrade", "fixture"), self.calls)
        self.assertFalse(any(call[:2] == ("marketplace", "add") for call in self.calls))
        self.assertEqual(self.state()["sources"][URL + ".git"]["ref"], SHA)
        self.assertEqual(self.installed, {"example@fixture"})

    def test_manual_ref_change_is_reconciled_to_preset(self):
        plugins.apply([self.entry()], self.home)
        self.config.write_text(self.config.read_text().replace('"main"', '"other"'))
        plugins.apply([self.entry()], self.home)
        self.assertIn('ref = "main"', self.config.read_text())

    def test_offline_refresh_keeps_and_reapplies_cached_plugin(self):
        plugins.apply([self.entry()], self.home)

        def offline(*args, **kwargs):
            if args[:2] == ("marketplace", "upgrade"):
                raise plugins.PresetError("offline")
            return self.native(*args)

        with patch.object(plugins, "codex", side_effect=offline):
            plugins.apply([self.entry()], self.home)
        self.assertEqual(self.installed, {"example@fixture"})

    def test_ref_change_preserves_other_config_and_rolls_back_on_failure(self):
        plugins.apply([self.entry()], self.home)
        before = self.config.read_text()

        def offline(*args, **kwargs):
            if args[:2] == ("marketplace", "upgrade"):
                self.assertIn('ref = "' + SHA + '"', self.config.read_text())
                raise plugins.PresetError("bad ref")
            return self.native(*args)

        with patch.object(plugins, "codex", side_effect=offline):
            plugins.apply([dict(repository=URL, ref=SHA)], self.home)
        self.assertEqual(self.config.read_text(), before)
        self.assertEqual(self.state()["sources"][URL + ".git"]["ref"], "main")
        self.assertEqual(self.installed, {"example@fixture"})
        plugins.apply([dict(repository=URL, ref=SHA)], self.home)
        self.assertEqual(
            self.config.read_text(),
            before.replace('ref = "main"', 'ref = "' + SHA + '"'),
        )
        self.assertEqual(self.state()["sources"][URL + ".git"]["ref"], SHA)

    def test_failed_install_does_not_block_another_source(self):
        def failing(*args, **kwargs):
            if args[:2] == ("marketplace", "add") and "broken" in args[2]:
                raise subprocess.TimeoutExpired("codex", 180)
            return self.native(*args)

        with patch.object(plugins, "codex", side_effect=failing):
            plugins.apply(
                [dict(repository="https://github.com/example/broken"), self.entry()],
                self.home,
            )
        self.assertEqual(self.installed, {"example@fixture"})

    def test_failed_remove_is_retried(self):
        plugins.apply([self.entry()], self.home)

        def failing(*args, **kwargs):
            if args[0] == "remove":
                raise plugins.PresetError("retry")
            return self.native(*args)

        with patch.object(plugins, "codex", side_effect=failing):
            plugins.apply([], self.home)
        self.assertIn("example@fixture", self.state()["plugins"])
        plugins.apply([], self.home)
        self.assertEqual(self.installed, set())

    def test_invalid_configuration_does_not_remove_existing_presets(self):
        plugins.apply([self.entry()], self.home)
        for entries in (
            None,
            [dict(repository=URL, ref="invalid..ref")],
            [self.entry(), dict(repository=URL, ref=SHA)],
            [dict(repository="file:///tmp/repo")],
        ):
            with self.subTest(entries=entries), self.assertRaises(plugins.PresetError):
                plugins.apply(entries, self.home)
        self.assertEqual(self.installed, {"example@fixture"})

    def test_native_upgrade_errors_are_not_silently_treated_as_success(self):
        self.mock.stop()
        with patch.object(plugins, "command") as run:
            run.return_value = subprocess.CompletedProcess(
                [], 0, '{"errors":[{"message":"failed"}]}'
            )
            with self.assertRaises(plugins.PresetError):
                plugins.codex("marketplace", "upgrade", "fixture")

    def test_deadline_bounds_cumulative_commands_and_preserves_ownership(self):
        plugins.apply([self.entry()], self.home)
        before = (self.home / "addon-plugin-presets.json").read_text()
        self.calls.clear()
        self.mock.stop()
        original = plugins.command

        def slow(args, deadline=None, limit=180):
            if args[0] == "git":
                return original(args, deadline, limit)
            response = json.dumps(self.native(*args[2:-1]))
            return original(
                [
                    sys.executable,
                    "-c",
                    f"import time; time.sleep(.2); print({response!r})",
                ],
                deadline,
                limit,
            )

        started = time.monotonic()
        with (
            patch.object(plugins, "STARTUP_TIMEOUT", 0.5),
            patch.object(plugins, "command", side_effect=slow),
            self.assertRaises(plugins.StartupTimeout),
        ):
            plugins.apply(
                [self.entry(), dict(repository="https://github.com/example/another")],
                self.home,
            )
        self.assertLess(time.monotonic() - started, 2)
        self.assertGreaterEqual(len(self.calls), 2)
        self.assertFalse(any(call[0] == "remove" for call in self.calls))
        self.assertEqual((self.home / "addon-plugin-presets.json").read_text(), before)

    def test_timeout_terminates_child_processes(self):
        marker = self.home / "late-child-write"
        ready = self.home / "child-started"
        child = [
            sys.executable,
            "-c",
            f"import time; from pathlib import Path; time.sleep(.8); Path({str(marker)!r}).touch()",
        ]
        parent = (
            "import subprocess, time; from pathlib import Path; "
            f"subprocess.Popen({child!r}); Path({str(ready)!r}).touch(); time.sleep(60)"
        )
        with self.assertRaises(plugins.StartupTimeout):
            plugins.command(
                [sys.executable, "-c", parent], deadline=time.monotonic() + 0.4
            )
        self.assertTrue(ready.exists())
        time.sleep(0.9)
        self.assertFalse(marker.exists())

    def test_no_presets_make_no_native_calls(self):
        plugins.apply([], self.home)
        self.assertEqual(self.calls, [])

    def test_invalid_ownership_state_leaves_plugins_unchanged(self):
        plugins.apply([self.entry()], self.home)
        (self.home / "addon-plugin-presets.json").write_text('{"plugins": {}}')
        self.calls.clear()
        with self.assertRaises(plugins.PresetError):
            plugins.apply([], self.home)
        self.assertEqual(self.calls, [])
        self.assertEqual(self.installed, {"example@fixture"})


if __name__ == "__main__":
    unittest.main()
