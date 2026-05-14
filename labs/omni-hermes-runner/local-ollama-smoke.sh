#!/usr/bin/env bash
set -euo pipefail

MODEL="${OMNI_LOCAL_MODEL:-qwen2.5-coder:3b}"
OLLAMA_URL="${OLLAMA_URL:-http://127.0.0.1:11434}"

echo "== Omni Local Ollama Smoke =="
echo "Model: $MODEL"
echo "URL: $OLLAMA_URL"
echo

curl -s "$OLLAMA_URL/api/generate" \
  -d "{
    \"model\": \"$MODEL\",
    \"prompt\": \"Return exactly: OMNI_LOCAL_MODEL_OK\",
    \"stream\": false
  }" | python3 -c 'import sys,json; print(json.load(sys.stdin).get("response",""))'
