#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="$ROOT_DIR/docker-compose.demo.yml"
VALIDATOR="$ROOT_DIR/scripts/docker-runtime-smoke-validator.mjs"
RUN_TOKEN="${GITHUB_RUN_ID:-local}-${GITHUB_RUN_ATTEMPT:-1}-$$"
RUN_TOKEN="${RUN_TOKEN//[^a-zA-Z0-9-]/-}"
PROJECT_NAME="omni-smoke-${RUN_TOKEN,,}"
export OMNI_SMOKE_IMAGE="omni-demo-smoke:${RUN_TOKEN,,}"
export OMNI_DEMO_HOST_PORT="$(node -e "const s=require('net').createServer();s.listen(0,'127.0.0.1',()=>{console.log(s.address().port);s.close()})")"
export OMNI_SMOKE_SENTINEL="smoke-sentinel-$(node -e "process.stdout.write(require('crypto').randomBytes(24).toString('hex'))")"
export OMNI_SMOKE_AUTH_MATERIAL="smoke-auth-$(node -e "process.stdout.write(require('crypto').randomBytes(48).toString('hex'))")"

WORK_DIR="$(mktemp -d "${TMPDIR:-/tmp}/omni-docker-smoke.XXXXXX")"
RAW_DIR="$WORK_DIR/raw"
OVERRIDE_FILE="$WORK_DIR/smoke.override.yml"
DIAGNOSTICS_DIR="${SMOKE_DIAGNOSTICS_DIR:-$WORK_DIR/diagnostics}"
mkdir -p "$RAW_DIR" "$DIAGNOSTICS_DIR"

COMPOSE=(docker compose --project-name "$PROJECT_NAME" --file "$COMPOSE_FILE" --file "$OVERRIDE_FILE")
CONTAINER_ID=""
IMAGE_ID=""
SMOKE_SUCCEEDED=false
STOP_COMPLETED=false

cat >"$OVERRIDE_FILE" <<'YAML'
services:
  omni-demo:
    image: ${OMNI_SMOKE_IMAGE:?OMNI_SMOKE_IMAGE is required}
    environment:
      SUPABASE_JWT_SECRET: ${OMNI_SMOKE_AUTH_MATERIAL:?OMNI_SMOKE_AUTH_MATERIAL is required}
      SUPABASE_URL: https://smoke-test.supabase.co
      OMNI_SMOKE_SENTINEL: ${OMNI_SMOKE_SENTINEL:?OMNI_SMOKE_SENTINEL is required}
YAML

sanitize_copy() {
  local source="$1" destination="$2"
  [[ -f "$source" ]] && node "$VALIDATOR" sanitize "$source" "$destination"
}

collect_diagnostics() {
  set +e
  docker version >"$RAW_DIR/docker-version.txt" 2>&1
  docker compose version >"$RAW_DIR/compose-version.txt" 2>&1
  docker compose --file "$COMPOSE_FILE" config >"$RAW_DIR/compose-config.txt" 2>&1
  "${COMPOSE[@]}" ps --all >"$RAW_DIR/compose-ps.txt" 2>&1
  if [[ -n "$CONTAINER_ID" ]]; then
    docker inspect --format '{"id":"{{.Id}}","image":"{{.Image}}","user":"{{.Config.User}}","status":"{{.State.Status}}","health":"{{if .State.Health}}{{.State.Health.Status}}{{end}}","exit_code":{{.State.ExitCode}},"oom_killed":{{.State.OOMKilled}},"restart_count":{{.RestartCount}},"read_only":{{.HostConfig.ReadonlyRootfs}},"cap_drop":{{json .HostConfig.CapDrop}},"security_opt":{{json .HostConfig.SecurityOpt}},"tmpfs":{{json .HostConfig.Tmpfs}},"ports":{{json .NetworkSettings.Ports}}}' "$CONTAINER_ID" >"$RAW_DIR/container-inspect.json" 2>&1
    "${COMPOSE[@]}" logs --no-color --timestamps >"$RAW_DIR/container-logs.txt" 2>&1
  fi
  for file in "$RAW_DIR"/*; do
    [[ -f "$file" ]] && sanitize_copy "$file" "$DIAGNOSTICS_DIR/$(basename "$file" | sed 's/container-inspect/container-inspect-sanitized/; s/container-logs/container-logs-sanitized/')"
  done
  node "$VALIDATOR" scan-dir "$DIAGNOSTICS_DIR"
}

cleanup() {
  local status=$?
  trap - EXIT ERR
  set +e
  if [[ "$SMOKE_SUCCEEDED" != true ]]; then
    collect_diagnostics
  fi
  "${COMPOSE[@]}" down --remove-orphans --volumes >/dev/null 2>&1
  if [[ -n "$IMAGE_ID" ]]; then docker image rm --force "$OMNI_SMOKE_IMAGE" >/dev/null 2>&1; fi
  rm -f "$OVERRIDE_FILE"
  unset OMNI_SMOKE_AUTH_MATERIAL OMNI_SMOKE_SENTINEL
  if [[ "$SMOKE_SUCCEEDED" == true || -n "${SMOKE_DIAGNOSTICS_DIR:-}" ]]; then rm -rf "$WORK_DIR"; fi
  exit "$status"
}
trap cleanup EXIT
trap 'echo "Docker runtime smoke failed at line $LINENO" >&2' ERR

request() {
  local method="$1" path="$2" output="$3" body="${4:-}"
  local args=(--silent --show-error --max-time 20 --output "$output" --write-out '%{http_code}' --request "$method")
  if [[ -n "$body" ]]; then args+=(--header 'Content-Type: application/json' --data-binary "@$body"); fi
  curl "${args[@]}" "http://127.0.0.1:${OMNI_DEMO_HOST_PORT}${path}"
}

echo "Recording Docker toolchain versions"
docker version >"$RAW_DIR/docker-version.txt"
docker compose version >"$RAW_DIR/compose-version.txt"

echo "Validating the canonical Compose profile"
docker compose --file "$COMPOSE_FILE" config >"$RAW_DIR/compose-config.txt"
grep -Eq 'dockerfile: Dockerfile\.demo' "$RAW_DIR/compose-config.txt"
"${COMPOSE[@]}" config --quiet

echo "Building explicit smoke image $OMNI_SMOKE_IMAGE"
"${COMPOSE[@]}" build --pull omni-demo
IMAGE_ID="$(docker image inspect --format '{{.Id}}' "$OMNI_SMOKE_IMAGE")"
[[ "$IMAGE_ID" == sha256:* ]]
docker history --no-trunc "$IMAGE_ID" >"$RAW_DIR/image-history.txt"

echo "Starting isolated Compose project $PROJECT_NAME on host port $OMNI_DEMO_HOST_PORT"
"${COMPOSE[@]}" up --detach --no-build omni-demo
CONTAINER_ID="$("${COMPOSE[@]}" ps --quiet omni-demo)"
[[ -n "$CONTAINER_ID" ]]

deadline=$((SECONDS + 120))
while (( SECONDS < deadline )); do
  state="$(docker inspect --format '{{.State.Status}}|{{if .State.Health}}{{.State.Health.Status}}{{end}}|{{.RestartCount}}' "$CONTAINER_ID")"
  if [[ "$state" == 'running|healthy|0' ]]; then break; fi
  [[ "$state" == running* || "$state" == created* ]] || { echo "Container left running state: $state" >&2; false; }
  sleep 2
done
[[ "${state:-}" == 'running|healthy|0' ]]

health_code="$(request GET /health "$RAW_DIR/health-response.json")"
[[ "$health_code" == 200 ]]
node "$VALIDATOR" health "$RAW_DIR/health-response.json"

status_code="$(request GET /api/v1/status "$RAW_DIR/status-response.json")"
[[ "$status_code" == 200 ]]
node "$VALIDATOR" status "$RAW_DIR/status-response.json"

printf '%s' '{"message":"Ol\u00e1!","client_session_id":"docker-smoke-client","request_id":"docker-smoke-request"}' >"$WORK_DIR/chat-request.json"
chat_code="$(request POST /chat "$RAW_DIR/chat-response.json" "$WORK_DIR/chat-request.json")"
[[ "$chat_code" == 200 ]]
node "$VALIDATOR" chat "$RAW_DIR/chat-response.json"

chat_v1_code="$(request POST /api/v1/chat "$RAW_DIR/chat-v1-response.json" "$WORK_DIR/chat-request.json")"
[[ "$chat_v1_code" == 200 ]]
node "$VALIDATOR" chat-v1 "$RAW_DIR/chat-v1-response.json"

printf '%s' '{"message":' >"$WORK_DIR/malformed.json"
malformed_code="$(request POST /chat "$RAW_DIR/negative-malformed-response.json" "$WORK_DIR/malformed.json")"
[[ "$malformed_code" == 400 ]]
node "$VALIDATOR" error "$RAW_DIR/negative-malformed-response.json" INVALID_JSON

node -e "require('fs').writeFileSync(process.argv[1], JSON.stringify({message:'x'.repeat(8001)}))" "$WORK_DIR/oversized.json"
oversized_code="$(request POST /chat "$RAW_DIR/negative-oversized-response.json" "$WORK_DIR/oversized.json")"
[[ "$oversized_code" == 413 ]]
node "$VALIDATOR" error "$RAW_DIR/negative-oversized-response.json" PAYLOAD_TOO_LARGE

[[ "$(docker inspect --format '{{.State.Status}}|{{.State.Health.Status}}|{{.RestartCount}}' "$CONTAINER_ID")" == 'running|healthy|0' ]]

echo "Verifying effective container hardening"
[[ "$(docker inspect --format '{{.Config.User}}' "$CONTAINER_ID")" == omni ]]
[[ "$(docker exec "$CONTAINER_ID" id -u)" != 0 ]]
[[ "$(docker inspect --format '{{.HostConfig.ReadonlyRootfs}}' "$CONTAINER_ID")" == true ]]
[[ "$(docker inspect --format '{{json .HostConfig.CapDrop}}' "$CONTAINER_ID")" == '["ALL"]' ]]
docker inspect --format '{{json .HostConfig.SecurityOpt}}' "$CONTAINER_ID" | grep -q 'no-new-privileges:true'
tmpfs_json="$(docker inspect --format '{{json .HostConfig.Tmpfs}}' "$CONTAINER_ID")"
for mount in /tmp /app/.logs /app/backend/python/memory /app/backend/python/transcripts /app/backend/python/brain/runtime/sessions /app/storage/local; do
  grep -Fq "\"$mount\"" <<<"$tmpfs_json"
done
docker inspect --format '{{json (index .NetworkSettings.Ports "3001/tcp")}}' "$CONTAINER_ID" | grep -Fq "\"HostPort\":\"$OMNI_DEMO_HOST_PORT\""
if docker exec "$CONTAINER_ID" sh -c 'touch /app/docker-smoke-protected'; then echo 'protected rootfs write unexpectedly succeeded' >&2; false; fi
docker exec "$CONTAINER_ID" sh -c 'probe=/tmp/docker-smoke-write; : >"$probe"; rm "$probe"'

"${COMPOSE[@]}" logs --no-color --timestamps >"$RAW_DIR/container-logs.txt"
for public_file in "$RAW_DIR"/*response.json "$RAW_DIR/container-logs.txt"; do
  node "$VALIDATOR" scan "$public_file"
done
if grep -Eqi 'unhandled exception|Traceback \(most recent call last\)|panicked at|Authorization:[[:space:]]*Bearer' "$RAW_DIR/container-logs.txt"; then
  echo 'fatal or sensitive marker found in container logs' >&2
  false
fi

echo "Stopping through Docker SIGTERM path"
restart_before="$(docker inspect --format '{{.RestartCount}}' "$CONTAINER_ID")"
docker stop --time 20 "$CONTAINER_ID" >/dev/null
STOP_COMPLETED=true
exit_code="$(docker inspect --format '{{.State.ExitCode}}' "$CONTAINER_ID")"
oom_killed="$(docker inspect --format '{{.State.OOMKilled}}' "$CONTAINER_ID")"
restart_after="$(docker inspect --format '{{.RestartCount}}' "$CONTAINER_ID")"
[[ "$exit_code" != 137 ]]
[[ "$exit_code" == 0 ]]
[[ "$oom_killed" == false ]]
[[ "$restart_after" == "$restart_before" ]]
sleep 2
[[ "$(docker inspect --format '{{.State.Status}}' "$CONTAINER_ID")" == exited ]]

cat >"$RAW_DIR/smoke-summary.txt" <<EOF
result=passed
project=$PROJECT_NAME
image_id=$IMAGE_ID
container_user=omni
health_http=$health_code
status_http=$status_code
chat_http=$chat_code
chat_v1_http=$chat_v1_code
malformed_http=$malformed_code
oversized_http=$oversized_code
runtime_truth=DIRECT_LOCAL_RESPONSE_WITH_PROVIDER_UNAVAILABLE
restart_count=$restart_after
shutdown_exit_code=$exit_code
oom_killed=$oom_killed
sentinel_scan=passed
EOF

collect_diagnostics
SMOKE_SUCCEEDED=true
echo "Docker runtime smoke passed: image=$IMAGE_ID shutdown_exit=$exit_code runtime_truth=DIRECT_LOCAL_RESPONSE_WITH_PROVIDER_UNAVAILABLE"
