import importlib.util
import tempfile
import unittest
from pathlib import Path


spec = importlib.util.spec_from_file_location(
    "release", Path(__file__).resolve().parents[1] / "scripts/release.py"
)
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)


class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.addon = self.root / "codex"
        self.addon.mkdir()
        (self.addon / "VERSION").write_text("0.1.0\n")
        (self.addon / "config.yaml").write_text(
            'version: dev\nslug: oai_codex_terminal\noptions:\n  model: ""\n'
        )
        (self.addon / "Dockerfile").write_text("RUN npm install -g @openai/codex@0.159.2\n")
        (self.addon / "CHANGELOG.md").write_text("# Changelog\n\n## 0.1.0\n\n- Initial release.\n")

    def test_first_release_is_pending_until_promoted(self):
        self.assertEqual(release.metadata(self.root)[:2], ("0.1.0", "dev"))
        release.promote(self.root)
        config = (self.addon / "config.yaml").read_text()
        self.assertIn('version: "0.1.0"', config)
        self.assertIn(f'image: "{release.IMAGE}"', config)
        self.assertIn("slug: oai_codex_terminal", config)
        self.assertIn('options:\n  model: ""', config)
        release.promote(self.root)
        self.assertEqual(config, (self.addon / "config.yaml").read_text())

    def test_update_bumps_patch_and_changelog_without_advertising(self):
        release.promote(self.root)
        config = (self.addon / "config.yaml").read_text()
        self.assertTrue(release.update(self.root, "0.160.0"))
        self.assertEqual(release.metadata(self.root)[:2], ("0.1.1", "0.1.0"))
        self.assertEqual(config, (self.addon / "config.yaml").read_text())
        self.assertIn("@openai/codex@0.160.0", (self.addon / "Dockerfile").read_text())
        self.assertIn("Update Codex CLI from 0.159.2 to 0.160.0", release.metadata(self.root)[3])

    def test_unpublished_release_prevents_stacked_updates(self):
        self.assertFalse(release.update(self.root, "0.160.0"))
        self.assertEqual((self.addon / "VERSION").read_text(), "0.1.0\n")

    def test_equal_and_older_codex_versions_do_not_release(self):
        release.promote(self.root)
        self.assertFalse(release.update(self.root, "0.159.2"))
        self.assertFalse(release.update(self.root, "0.159.1"))

    def test_reject_missing_changelog_and_release_rollback(self):
        release.promote(self.root)
        (self.addon / "VERSION").write_text("0.0.9\n")
        with self.assertRaisesRegex(ValueError, "older"):
            release.metadata(self.root)
        (self.addon / "VERSION").write_text("0.1.1\n")
        with self.assertRaisesRegex(ValueError, "Missing changelog"):
            release.metadata(self.root)

    def test_reject_unstable_or_malformed_versions_before_mutation(self):
        release.promote(self.root)
        for value in ("latest", "0.160.0-beta.1", "01.2.3", "1.2"):
            with self.assertRaises(ValueError):
                release.update(self.root, value)
        self.assertEqual((self.addon / "VERSION").read_text(), "0.1.0\n")


if __name__ == "__main__":
    unittest.main()
