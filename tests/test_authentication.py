"""Verify login reuse and persistent storage using the actual startup scripts."""

import json
import subprocess
import sys
import unittest

import test_permissions

ROOT = test_permissions.ROOT


class AuthenticationTests(unittest.TestCase):
    stub = test_permissions.PermissionsTests.stub
    launch = test_permissions.PermissionsTests.launch

    def setUp(self):
        test_permissions.PermissionsTests.setUp(self)
        self.persistent = self.work / "persistent"
        self.legacy = self.work / "legacy"
        self.legacy.mkdir()
        self.sessions = self.work / "sessions"
        self.sessions.mkdir()
        (self.sessions / "existing-session.jsonl").write_text("history\n")
        self.auth = self.persistent / "auth.json"
        self.stub("codex", f'''#!{sys.executable}
import json, os, pathlib, sys
args = sys.argv[1:]
assert args[:2] == ['-c', 'cli_auth_credentials_store="file"'], args
args = args[2:]
auth = pathlib.Path(os.environ['CODEX_HOME']) / 'auth.json'
if args == ['login', 'status']:
    sys.exit(0 if auth.exists() else 1)
if args == ['login', '--with-api-key']:
    assert sys.stdin.read().strip() == 'sk-test'
    auth.write_text(json.dumps({{'auth_mode': 'apikey'}}))
    print('NEW_LOGIN')
    sys.exit(0)
raise AssertionError(args)
''')
        self.stub("ttyd", '#!/bin/sh\nprintf "HOME:%s\\n" "$CODEX_HOME"\n')
        source = (ROOT / "codex/run.sh").read_text()
        source = source.replace("/data/.codex-sessions", str(self.sessions))
        source = source.replace("/data/.codex", str(self.persistent))
        source = source.replace("/root/.codex", str(self.legacy))
        self.startup = self.work / "run.sh"
        self.startup.write_text(source)
        self.functions = self.work / "bashio.sh"
        self.functions.write_text('''bashio::log.info() { :; }
bashio::log.warning() { :; }
bashio::config() { :; }
''')
        self.env['CODEX_HOME'] = str(self.persistent)

    def start_container(self):
        result = subprocess.run(
            ['bash', str(self.startup)], text=True, capture_output=True,
            env=dict(self.env, BASH_ENV=str(self.functions)), timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(f'HOME:{self.persistent}', result.stdout)

    def test_chatgpt_login_survives_recreation_without_api_key_overwrite(self):
        self.start_container()
        # Simulate an interactive ChatGPT login in the first container.
        credential = '{"auth_mode":"chatgpt","tokens":{"refresh_token":"fake"}}'
        self.auth.write_text(credential)
        # The replacement container has no credentials in its legacy home.
        self.start_container()
        result = self.launch(OPENAI_API_KEY='sk-test')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('Reusing saved Codex login.', result.stdout)
        self.assertNotIn('NEW_LOGIN', result.stdout)
        self.assertEqual(self.auth.read_text(), credential)
        self.assertEqual(self.auth.stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.persistent.stat().st_mode & 0o777, 0o700)
        self.assertEqual((self.persistent / 'sessions' / 'existing-session.jsonl')
                         .read_text(), 'history\n')

    def test_api_key_bootstrap_is_cached_for_future_starts(self):
        self.start_container()
        first = self.launch(OPENAI_API_KEY='sk-test')
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertIn('NEW_LOGIN', first.stdout)
        self.assertEqual(json.loads(self.auth.read_text())['auth_mode'], 'apikey')
        self.start_container()
        second = self.launch()
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertIn('Reusing saved Codex login.', second.stdout)
        self.assertNotIn('NEW_LOGIN', second.stdout)

    def test_first_start_without_credentials_offers_interactive_sign_in(self):
        self.start_container()
        result = self.launch()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('Choose a sign-in method', result.stdout)
        self.assertIn('ARGS:', result.stdout)
        self.assertFalse(self.auth.exists())

    def test_legacy_migration_does_not_restore_credentials_after_logout(self):
        (self.legacy / 'auth.json').write_text('{"auth_mode":"chatgpt"}')
        (self.legacy / 'config.toml').write_text('model = "test-model"\n')
        self.start_container()
        self.assertEqual(self.auth.read_text(), '{"auth_mode":"chatgpt"}')
        self.assertEqual((self.persistent / 'config.toml').read_text(),
                         'model = "test-model"\n')
        self.auth.unlink()  # Simulate logout.
        self.start_container()
        self.assertFalse(self.auth.exists())


if __name__ == '__main__':
    unittest.main()
