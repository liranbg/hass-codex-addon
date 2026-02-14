#!/usr/bin/env bash
#
# Test: resume_last_session feature works out of the box
#
# Verifies that:
#   1. Session directory is persisted to /data/.codex-sessions
#   2. codex.sh builds the correct command args when resume is enabled/disabled
#
set -euo pipefail

IMAGE="${1:-hass-codex-addon:dev}"
PASS=0
FAIL=0

pass() { echo "  PASS: $1"; PASS=$((PASS + 1)); }
fail() { echo "  FAIL: $1"; FAIL=$((FAIL + 1)); }

cleanup() {
  docker rm -f test-resume-session >/dev/null 2>&1 || true
}
trap cleanup EXIT

# Helper: run codex.sh with a node stub that prints args, then return output
run_codex_stub() {
  local resume_val="$1"
  local model_val="$2"

  docker run --rm --name test-resume-session \
    -e CODEX_RESUME_LAST="$resume_val" \
    -e CODEX_MODEL="$model_val" \
    -e OPENAI_API_KEY="sk-test" \
    --entrypoint sh \
    "$IMAGE" -c '
      # Stub node to capture args passed to codex
      mv /usr/bin/node /usr/bin/node.real
      printf "#!/bin/sh\necho \"NODE_ARGS: \$@\"\nexit 1\n" > /usr/bin/node
      chmod +x /usr/bin/node

      # Stub codex for the login calls (which use codex directly, not node)
      real_codex=$(which codex)
      printf "#!/bin/sh\nexit 0\n" > "$real_codex"
      chmod +x "$real_codex"

      echo "!exit" | bash /codex.sh 2>&1
    ' 2>&1
}

echo "=== Test: resume_last_session feature ==="
echo ""

# --- Test 1: Session symlink is created on startup ---
echo "[1] Session directory symlink is created"
cleanup

docker run -d --name test-resume-session \
  --entrypoint sh \
  "$IMAGE" -c "
    mkdir -p /data/.codex-sessions
    mkdir -p /root/.codex
    ln -sfn /data/.codex-sessions /root/.codex/sessions
    sleep 30
  " >/dev/null

sleep 2

target=$(docker exec test-resume-session readlink /root/.codex/sessions 2>/dev/null || echo "")
if [[ "$target" == "/data/.codex-sessions" ]]; then
  pass "symlink /root/.codex/sessions -> /data/.codex-sessions"
else
  fail "symlink target is '$target', expected '/data/.codex-sessions'"
fi

docker exec test-resume-session touch /root/.codex/sessions/.write-test 2>/dev/null
if docker exec test-resume-session test -f /data/.codex-sessions/.write-test; then
  pass "session directory is writable via symlink"
else
  fail "session directory is not writable via symlink"
fi

cleanup

# --- Test 2: codex.sh passes resume --last when enabled ---
echo "[2] codex.sh includes 'resume --last' when CODEX_RESUME_LAST=true"

output=$(run_codex_stub "true" "")
if echo "$output" | grep -q "NODE_ARGS:.*resume --last"; then
  pass "codex invoked with 'resume --last'"
else
  fail "codex was NOT invoked with 'resume --last'. Output: $(echo "$output" | grep NODE_ARGS)"
fi

# --- Test 3: codex.sh does NOT pass resume --last when disabled ---
echo "[3] codex.sh omits 'resume --last' when CODEX_RESUME_LAST=false"

output=$(run_codex_stub "false" "")
if echo "$output" | grep -q "NODE_ARGS:" && ! echo "$output" | grep -q "resume --last"; then
  pass "codex invoked WITHOUT 'resume --last'"
else
  fail "unexpected output: $(echo "$output" | grep NODE_ARGS)"
fi

# --- Test 4: codex.sh passes model AND resume --last together ---
echo "[4] codex.sh passes both -m MODEL and resume --last"

output=$(run_codex_stub "true" "gpt-5")
if echo "$output" | grep -q "NODE_ARGS:.*-m gpt-5" && echo "$output" | grep -q "NODE_ARGS:.*resume --last"; then
  pass "codex invoked with '-m gpt-5' and 'resume --last'"
else
  fail "expected both '-m gpt-5' and 'resume --last'. Output: $(echo "$output" | grep NODE_ARGS)"
fi

# --- Summary ---
echo ""
echo "=== Results: $PASS passed, $FAIL failed ==="
exit "$FAIL"
