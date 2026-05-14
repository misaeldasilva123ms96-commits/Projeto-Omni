#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

HERMES_BIN="/root/hermes-agent/.venv/bin/hermes"

echo "== Omni-Hermes Runner =="
echo "Root: $ROOT_DIR"
echo "Branch: $(git branch --show-current)"
echo

export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"
nvm use 20 >/dev/null 2>&1 || true

# Keep Omni Python venv active for Omni tests.
if [ -f "$ROOT_DIR/.venv/bin/activate" ]; then
  . "$ROOT_DIR/.venv/bin/activate"
fi

export PATH="$HOME/.local/bin:$PATH"

echo "== Runtime versions =="
node -v || true
npm -v || true
python --version || python3 --version || true
"$HERMES_BIN" --version || true
echo

echo "== Python path check =="
which python || true
python -m pip --version || true
echo

echo "== Git status =="
git status --short
echo

echo "== Omni JS runtime check =="
npm run test:js-runtime || true
echo

echo "== Omni Python pytest check =="
python -m pip install -q pytest pytest-cov || true
npm run test:python:pytest || true
echo

echo "== Hermes smoke test =="
if [ -x "$HERMES_BIN" ]; then
  "$HERMES_BIN" --help | head -80 || true
else
  echo "Hermes binary not found: $HERMES_BIN"
fi
