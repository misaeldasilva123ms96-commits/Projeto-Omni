#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
source "$ROOT_DIR/scripts/docker-runtime-smoke-cleanup.sh"

teardown_attempts=0
verify_attempts=0
image_attempts=0

teardown_ok() { teardown_attempts=$((teardown_attempts + 1)); }
verify_ok() { verify_attempts=$((verify_attempts + 1)); }
image_ok() { image_attempts=$((image_attempts + 1)); }
teardown_fail() { teardown_attempts=$((teardown_attempts + 1)); return 1; }
diagnostics_fail() { return 1; }

assert_all_cleanup_attempted() {
  [[ "$teardown_attempts" == 1 ]]
  [[ "$verify_attempts" == 1 ]]
  [[ "$image_attempts" == 1 ]]
}

if omni_finalize_cleanup 0 teardown_fail verify_ok image_ok; then
  echo 'cleanup failure unexpectedly preserved a successful smoke result' >&2
  exit 1
else
  status=$?
fi
[[ "$status" == 1 ]]
assert_all_cleanup_attempted

teardown_attempts=0
verify_attempts=0
image_attempts=0
if omni_finalize_cleanup 23 teardown_fail verify_ok image_ok; then
  echo 'existing smoke failure unexpectedly became successful' >&2
  exit 1
else
  status=$?
fi
[[ "$status" == 23 ]]
assert_all_cleanup_attempted

teardown_attempts=0
verify_attempts=0
image_attempts=0
if omni_finalize_failed_smoke 37 diagnostics_fail teardown_ok verify_ok image_ok; then
  echo 'sanitizer failure unexpectedly replaced the original smoke failure' >&2
  exit 1
else
  status=$?
fi
[[ "$status" == 37 ]]
assert_all_cleanup_attempted

echo 'Docker smoke cleanup status tests passed'
