"""Exercise the actual startup scripts without Docker or OpenAI requests."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class PermissionsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        self.bin = self.work / "bin"
        self.bin.mkdir()
        (self.work / "AGENTS.md").touch()
        self.env = dict(os.environ)
        for key in list(self.env):
            if key.startswith("CODEX_") or key == "OPENAI_API_KEY":
                del self.env[key]
        self.env.update(PATH=f"{self.bin}:{self.env['PATH']}",
                        CODEX_WORKING_DIR=str(self.work))
        for name in ("codex", "clear", "sleep"):
            self.stub(name, "#!/bin/sh\nexit 0\n")
        self.stub("node", f"#!{sys.executable}\nimport json, sys\n"
                  "print('ARGS:' + json.dumps(sys.argv[2:]))\n")

    def stub(self, name, content):
        path = self.bin / name
        path.write_text(content)
        path.chmod(0o755)

    def launch(self, **settings):
        return subprocess.run(
            ["bash", str(ROOT / "codex/codex.sh")], input="!exit\n",
            text=True, capture_output=True, env=dict(self.env, **settings),
            timeout=10,
        )

    def test_review_network_and_resume_combinations(self):
        for review, reviewer in (("ask", "user"), ("approve", "auto_review")):
            for network in ("false", "true"):
                for resume in ("false", "true"):
                    with self.subTest(review=review, network=network, resume=resume):
                        result = self.launch(
                            CODEX_REVIEW_APPROVALS=review,
                            CODEX_ALLOW_INTERNET_ACCESS=network,
                            CODEX_RESUME_LAST=resume, CODEX_MODEL="test-model",
                        )
                        self.assertEqual(result.returncode, 0, result.stderr)
                        line = next(x for x in result.stdout.splitlines()
                                    if x.startswith("ARGS:"))
                        args = json.loads(line[5:])
                        expected = [
                            "--no-daemon",
                            "-c", 'cli_auth_credentials_store="file"',
                            "--sandbox", "workspace-write",
                            "--ask-for-approval", "on-request",
                            "-c", f'approvals_reviewer="{reviewer}"',
                            "-c", f"sandbox_workspace_write.network_access={network}",
                            "-m", "test-model",
                        ]
                        if resume == "true":
                            expected += ["resume", "--last"]
                        self.assertEqual(args, expected)

    def test_defaults_enable_automatic_review_and_network(self):
        result = self.launch()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('approvals_reviewer=\\"auto_review\\"', result.stdout)
        self.assertIn("sandbox_workspace_write.network_access=true", result.stdout)

    def test_invalid_settings_fail_before_codex_starts(self):
        for settings in ({"CODEX_REVIEW_APPROVALS": "never"},
                         {"CODEX_ALLOW_INTERNET_ACCESS": "yes"}):
            with self.subTest(settings=settings):
                result = self.launch(**settings)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("ERROR:", result.stdout)
                self.assertNotIn("ARGS:", result.stdout)

    def test_supervisor_options_are_exported_to_terminal(self):
        source = (ROOT / "codex/run.sh").read_text()
        # Isolate paths under the test directory; leave config/export code intact.
        source = source.replace("/data/.codex-sessions", str(self.work / "sessions"))
        source = source.replace("/data/.codex", str(self.work / "persistent"))
        source = source.replace("/root/.codex", str(self.work / "home"))
        startup = self.work / "run.sh"
        startup.write_text(source)
        functions = self.work / "bashio.sh"
        functions.write_text('''bashio::log.info() { :; }
bashio::log.warning() { :; }
bashio::config() {
  case "$1" in
    review_approvals) printf '%s' "${TEST_REVIEW:-}" ;;
    allow_internet_access) printf '%s' "${TEST_NETWORK:-}" ;;
  esac
}
''')
        self.stub("ttyd", '#!/bin/sh\nprintf "OPTIONS:%s:%s\\n" '
                  '"$CODEX_REVIEW_APPROVALS" "$CODEX_ALLOW_INTERNET_ACCESS"\n')
        for values, expected in (({}, "approve:true"),
                                 ({"TEST_REVIEW": "ask", "TEST_NETWORK": "false"},
                                  "ask:false")):
            result = subprocess.run(
                ["bash", str(startup)], text=True, capture_output=True,
                env=dict(self.env, BASH_ENV=str(functions), **values), timeout=10,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(f"OPTIONS:{expected}", result.stdout)


if __name__ == "__main__":
    unittest.main()
