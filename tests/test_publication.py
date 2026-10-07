"""Exercise the publication guard with real local Git repositories."""

import os
import re
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


WORKFLOW = Path(__file__).resolve().parents[1] / ".github/workflows/release.yaml"


def step_script(name):
    step = WORKFLOW.read_text().split(f"      - name: {name}\n", 1)[1]
    script = step.split("        run: |\n", 1)[1]
    script = re.split(r"\n      - name:", script, maxsplit=1)[0]
    return textwrap.dedent(script)


class PublicationTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.remote = self.root / "remote.git"
        self.work = self.root / "work"
        self.work.mkdir()
        self.git("init", "--bare", str(self.remote))
        self.git("init", "-b", "main")
        self.git("config", "user.email", "test@example.com")
        self.git("config", "user.name", "Test")
        self.git("remote", "add", "origin", str(self.remote))
        self.commit("source")
        self.source = self.git("rev-parse", "HEAD")
        self.git("push", "origin", "HEAD:main")
        self.commit("metadata")
        self.publication = self.git("rev-parse", "HEAD")
        self.branch = "auto/publish-test"
        self.git("push", "origin", f"HEAD:{self.branch}")

    def git(self, *args):
        return subprocess.check_output(
            ["git", *args], cwd=self.work, text=True, stderr=subprocess.DEVNULL
        ).strip()

    def commit(self, value):
        (self.work / "config.yaml").write_text(value)
        self.git("add", "config.yaml")
        self.git("commit", "-m", value)

    def publish(self):
        env = dict(
            os.environ,
            GITHUB_SHA=self.source,
            PUBLICATION_SHA=self.publication,
            BRANCH=self.branch,
        )
        return subprocess.run(
            [
                "bash", "-e", "-o", "pipefail", "-c",
                step_script("Publish checked metadata to Home Assistant"),
            ],
            cwd=self.work,
            env=env,
            text=True,
            capture_output=True,
        )

    def main_sha(self):
        return self.git("ls-remote", "origin", "refs/heads/main").split()[0]

    def test_success_pushes_the_checked_commit_and_removes_staging_branch(self):
        result = self.publish()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.main_sha(), self.publication)
        self.assertEqual(self.git("ls-remote", "origin", f"refs/heads/{self.branch}"), "")

    def test_main_advance_refuses_stale_publication(self):
        self.git("checkout", "--detach", self.source)
        self.commit("new runtime")
        newer = self.git("rev-parse", "HEAD")
        self.git("push", "origin", "HEAD:main")
        self.git("checkout", "--detach", self.publication)
        result = self.publish()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("refusing to advertise stale images", result.stdout)
        self.assertEqual(self.main_sha(), newer)

    def test_changed_local_commit_cannot_publish_without_checks(self):
        self.commit("unchecked change")
        result = self.publish()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.main_sha(), self.source)


class PublicationCITests(unittest.TestCase):
    def test_publication_push_starts_ruleset_eligible_ci(self):
        ci = WORKFLOW.with_name("ci.yaml").read_text()
        self.assertIn('  push:\n    branches: ["auto/publish-*"]', ci)
        announce = WORKFLOW.read_text().split("  announce:\n", 1)[1]
        self.assertIn("token: ${{ secrets.CODEX_UPDATE_TOKEN }}", announce)
        script = step_script("Run CI on the exact publication commit")
        self.assertIn("--event push", script)
        self.assertNotIn("gh workflow run", script)

    def test_failed_or_missing_ci_cannot_reach_publication(self):
        script = step_script("Run CI on the exact publication commit")
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            gh = root / "gh"
            gh.write_text(
                "#!/bin/sh\n"
                "printf '%s\\n' \"$*\" >> \"$TRACE\"\n"
                'case "$1 $2" in\n'
                '  "run list") printf "%s" "$RUN_ID"; exit "$LIST_STATUS" ;;\n'
                '  "run watch") exit "$CI_STATUS" ;;\n'
                "  *) exit 99 ;;\n"
                "esac\n"
            )
            gh.chmod(0o755)
            sleep = root / "sleep"
            sleep.write_text("#!/bin/sh\nexit 0\n")
            sleep.chmod(0o755)
            for listing, run_id, ci_status, expected in (
                (0, "123", 0, 0),
                (0, "123", 1, 1),
                (0, "", 0, 1),
                (1, "123", 0, 1),
            ):
                with self.subTest(listing=listing, run_id=run_id, ci=ci_status):
                    trace = root / f"trace-{listing}-{run_id}-{ci_status}"
                    env = dict(
                        os.environ,
                        PATH=f"{root}{os.pathsep}{os.environ['PATH']}",
                        BRANCH="auto/publish-test",
                        PUBLICATION_SHA="a" * 40,
                        TRACE=str(trace),
                        LIST_STATUS=str(listing),
                        RUN_ID=run_id,
                        CI_STATUS=str(ci_status),
                    )
                    result = subprocess.run(
                        ["bash", "-e", "-o", "pipefail", "-c", script],
                        env=env,
                        text=True,
                        capture_output=True,
                    )
                    self.assertEqual(result.returncode, expected, result.stderr)
                    calls = trace.read_text()
                    self.assertNotIn("workflow run", calls)
                    self.assertIn("run list --workflow ci.yaml --event push", calls)
                    self.assertIn("--branch auto/publish-test", calls)
                    if listing == 0 and run_id:
                        self.assertIn("run watch 123 --interval 10 --exit-status", calls)
                        self.assertIn("a" * 40, calls)
                    else:
                        self.assertNotIn("run watch", calls)


if __name__ == "__main__":
    unittest.main()
