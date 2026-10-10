#!/usr/bin/env bash
# Draft bounded wrapper. Execute only after independent review GO and root slot.
set -Eeuo pipefail
set +x
umask 077
unset ACTIONS_TEST_DATABASE_URL

readonly IMAGE='docker.io/library/postgres@sha256:aa90e97ee862e558111d34cfb8b2c4bec768c2b039fb791341686928560263b3'
readonly EXPECTED_HEAD='4e8a26296608c232ce3dbd1f250ddb709b9459c9'
readonly EXPECTED_TREE='1b582dd02b367e5216e60796a8da031e520aa12f'
readonly REPO='/workspace/work/actions-mk3-database-gates'
readonly HARNESS='/workspace/work/actions-mk3-evidence/database-gates/pg_migration_two_process.py'
readonly EVIDENCE_ROOT='/workspace/work/actions-mk3-evidence/database-gates'

if [[ -z "${ACTIONS84_PYTHON:-}" || ! -x "$ACTIONS84_PYTHON" ]]; then
  echo 'ACTIONS84_PYTHON must name the executable from the reviewed canonical RCC environment' >&2
  exit 2
fi
[[ "$ACTIONS84_PYTHON" == '/workspace/work/actions-mk3-pr302/action_server/.venv/bin/python' ]]
command -v docker >/dev/null
command -v timeout >/dev/null
command -v python3 >/dev/null
docker_bounded() {
  local seconds="$1"
  shift
  timeout --signal=TERM --kill-after=5 "$seconds" docker "$@"
}

cd "$REPO"
actual_head=$(git rev-parse HEAD)
actual_tree=$(git rev-parse 'HEAD^{tree}')
[[ "$actual_head" == "$EXPECTED_HEAD" && "$actual_tree" == "$EXPECTED_TREE" ]]
[[ -z "$(git status --porcelain)" ]]

run_id="$(date -u +%Y%m%dT%H%M%SZ)-$$"
evidence_dir="$EVIDENCE_ROOT/execution-$run_id"
mkdir -m 700 "$evidence_dir"
container_name="actions84-migration-$run_id"
container_id=''
credential_file=''
raw_test_log="$evidence_dir/.test.raw"
raw_server_log="$evidence_dir/.postgres.raw"
test_status='NOT_RUN'
test_log_status='NOT_CAPTURED'
server_log_status='NOT_CAPTURED'
cleanup_status='NOT_ATTEMPTED'
credential_cleanup='NOT_CREATED'
published_port=''
image_id=''
reported_version=''
image_platform=''

sanitize_file() {
  local raw_path="$1" safe_path="$2"
  SANITIZE_RAW="$raw_path" SANITIZE_OUT="$safe_path" \
    SANITIZE_DATABASE_URL="${database_url:-}" \
    SANITIZE_SECRET_PASSWORD="${db_password:-}" python3 - <<'PY'
import os
from pathlib import Path
from urllib.parse import urlsplit

raw = Path(os.environ['SANITIZE_RAW']).read_text(errors='replace')
url = os.environ.get('SANITIZE_DATABASE_URL', '')
password = urlsplit(url).password if url else None
for secret in (url, password or '', os.environ.get('SANITIZE_SECRET_PASSWORD', '')):
    if secret:
        raw = raw.replace(secret, '[REDACTED]')
Path(os.environ['SANITIZE_OUT']).write_text(raw[:1048576] + ('\n[TRUNCATED]\n' if len(raw) > 1048576 else ''))
PY
  chmod 600 "$safe_path"
}

write_receipt() {
  export GATE_EVIDENCE_DIR="$evidence_dir" GATE_IMAGE="$IMAGE"
  export GATE_HEAD="$actual_head" GATE_TREE="$actual_tree"
  export GATE_CONTAINER_NAME="$container_name" GATE_CONTAINER_ID="$container_id"
  export GATE_IMAGE_ID="$image_id" GATE_VERSION="$reported_version"
  export GATE_IMAGE_PLATFORM="$image_platform"
  export GATE_PORT="$published_port" GATE_TEST_STATUS="$test_status"
  export GATE_TEST_LOG_STATUS="$test_log_status" GATE_SERVER_LOG_STATUS="$server_log_status"
  export GATE_CLEANUP_STATUS="$cleanup_status" GATE_CREDENTIAL_CLEANUP="$credential_cleanup"
  env -u ACTIONS_TEST_DATABASE_URL "$ACTIONS84_PYTHON" - <<'PY'
import json, os, platform, subprocess, sys
from pathlib import Path

root = Path(os.environ['GATE_EVIDENCE_DIR'])
receipt = {
  'source': {'head': os.environ['GATE_HEAD'], 'tree': os.environ['GATE_TREE'], 'dirty': False},
  'interpreter': {'path': sys.executable, 'version': sys.version, 'platform': platform.platform()},
  'image': {'reference': os.environ['GATE_IMAGE'], 'container_image_id': os.environ['GATE_IMAGE_ID'], 'platform': os.environ['GATE_IMAGE_PLATFORM'], 'postgres_version': os.environ['GATE_VERSION']},
  'service': {'container_name': os.environ['GATE_CONTAINER_NAME'], 'container_id': os.environ['GATE_CONTAINER_ID'], 'loopback_port': os.environ['GATE_PORT'], 'memory_limit': '512m', 'cpu_limit': 1, 'pids_limit': 64},
  'test_status': os.environ['GATE_TEST_STATUS'],
  'test_log_status': os.environ['GATE_TEST_LOG_STATUS'],
  'server_log_status': os.environ['GATE_SERVER_LOG_STATUS'],
  'owned_container_cleanup': os.environ['GATE_CLEANUP_STATUS'],
  'credential_file_cleanup': os.environ['GATE_CREDENTIAL_CLEANUP'],
}
for name in ('test.log', 'postgres.log', 'migration-worker-receipt.json', 'harness-child-cleanup.json', 'interpreter-version.txt', 'image-pull.log'):
    path = root / name
    if path.is_file():
        import hashlib
        receipt.setdefault('artifacts', {})[name] = {'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'bytes': path.stat().st_size}
(root / 'execution-receipt.json').write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
PY
  chmod 600 "$evidence_dir/execution-receipt.json"
}

cleanup() {
  local code=$?
  local cleanup_failed=0
  local found_ids='' found_id='' found_owner='' found_name='' remaining_ids=''
  set +e
  if [[ -f "$raw_test_log" ]]; then
    if sanitize_file "$raw_test_log" "$evidence_dir/test.log"; then test_log_status='SANITIZED'; else test_log_status='SANITIZE_FAILED'; cleanup_failed=1; fi
  fi
  if [[ -n "$container_id" ]]; then
    found_owner=$(docker_bounded 10 container inspect --format '{{index .Config.Labels "org.openai.codex.task"}}' "$container_id" 2>/dev/null)
    found_name=$(docker_bounded 10 container inspect --format '{{.Name}}' "$container_id" 2>/dev/null)
    if [[ "$found_owner" == "actions84-migration-$run_id" && "$found_name" == "/$container_name" ]]; then
      if docker_bounded 20 logs "$container_id" >"$raw_server_log" 2>&1; then server_log_status='CAPTURED'; else server_log_status='CAPTURE_FAILED'; cleanup_failed=1; fi
      if sanitize_file "$raw_server_log" "$evidence_dir/postgres.log"; then server_log_status="${server_log_status}_SANITIZED"; else server_log_status='SANITIZE_FAILED'; cleanup_failed=1; fi
      docker_bounded 20 rm -f "$container_id" >/dev/null 2>&1
      if remaining_ids=$(docker_bounded 10 container ls --all --quiet --filter "id=$container_id" 2>/dev/null); then
        if [[ -z "$remaining_ids" ]]; then cleanup_status='REMOVED_AND_VERIFIED_ABSENT'; else cleanup_status='REMOVE_FAILED_CONTAINER_STILL_PRESENT'; cleanup_failed=1; fi
      else
        cleanup_status='REMOVE_READBACK_FAILED'
        cleanup_failed=1
      fi
    else
      cleanup_status='OWNERSHIP_IDENTITY_UNVERIFIED_LEFT_UNTOUCHED'
      cleanup_failed=1
    fi
  elif [[ -n "$container_name" ]]; then
    if found_ids=$(docker_bounded 10 container ls --all --quiet --filter "name=$container_name" 2>/dev/null); then
      if [[ -z "$found_ids" ]]; then
        cleanup_status='NO_CONTAINER_FOUND_BY_EXACT_UNIQUE_NAME'
      else
        found_id=$(printf '%s\n' "$found_ids" | head -n 1)
        found_owner=$(docker_bounded 10 container inspect --format '{{index .Config.Labels "org.openai.codex.task"}}' "$found_id" 2>/dev/null)
        found_name=$(docker_bounded 10 container inspect --format '{{.Name}}' "$found_id" 2>/dev/null)
        if [[ "$found_owner" == "actions84-migration-$run_id" && "$found_name" == "/$container_name" ]]; then
          container_id="$found_id"
          if docker_bounded 20 logs "$found_id" >"$raw_server_log" 2>&1; then server_log_status='CAPTURED'; else server_log_status='CAPTURE_FAILED'; cleanup_failed=1; fi
          if sanitize_file "$raw_server_log" "$evidence_dir/postgres.log"; then server_log_status="${server_log_status}_SANITIZED"; else server_log_status='SANITIZE_FAILED'; cleanup_failed=1; fi
          docker_bounded 20 rm -f "$found_id" >/dev/null 2>&1
          if remaining_ids=$(docker_bounded 10 container ls --all --quiet --filter "id=$found_id" 2>/dev/null); then
            if [[ -z "$remaining_ids" ]]; then cleanup_status='REMOVED_AND_VERIFIED_ABSENT'; else cleanup_status='REMOVE_FAILED_CONTAINER_STILL_PRESENT'; cleanup_failed=1; fi
          else
            cleanup_status='REMOVE_READBACK_FAILED'
            cleanup_failed=1
          fi
        else
          cleanup_status='UNOWNED_OR_UNVERIFIED_CONTAINER_LEFT_UNTOUCHED'
          cleanup_failed=1
        fi
      fi
    else
      cleanup_status='DOCKER_NAME_LOOKUP_FAILED'
      cleanup_failed=1
    fi
  else
    cleanup_status='NO_NAME_FOR_CONTAINER_LOOKUP'
    cleanup_failed=1
  fi
  if [[ -n "$credential_file" && -f "$credential_file" ]]; then
    if rm -f -- "$credential_file"; then credential_cleanup='REMOVED_MODE_0600'; else credential_cleanup='REMOVE_FAILED'; cleanup_failed=1; fi
  fi
  rm -f -- "$raw_test_log" "$raw_server_log"
  if ! write_receipt; then cleanup_failed=1; fi
  if [[ "$cleanup_failed" -eq 1 ]]; then exit 125; fi
  return "$code"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

credential_file=$(mktemp "$evidence_dir/.postgres-env.XXXXXX")
chmod 600 "$credential_file"
db_user='actions84'
db_name='actions84'
db_password=$(od -An -N24 -tx1 /dev/urandom | tr -d ' \n')
[[ ${#db_password} -eq 48 ]]
printf 'POSTGRES_USER=%s\nPOSTGRES_PASSWORD=%s\nPOSTGRES_DB=%s\n' "$db_user" "$db_password" "$db_name" >"$credential_file"

docker_bounded 180 pull "$IMAGE" >"$evidence_dir/image-pull.log" 2>&1
chmod 600 "$evidence_dir/image-pull.log"
repo_digests=$(docker_bounded 10 image inspect --format '{{json .RepoDigests}}' "$IMAGE")
[[ "$repo_digests" == *'postgres@sha256:aa90e97ee862e558111d34cfb8b2c4bec768c2b039fb791341686928560263b3'* ]]
image_id=$(docker_bounded 10 image inspect --format '{{.Id}}' "$IMAGE")
image_platform=$(docker_bounded 10 image inspect --format '{{.Os}}/{{.Architecture}}' "$IMAGE")
[[ "$image_platform" == 'linux/amd64' ]]

container_id=$(docker_bounded 20 run --detach --name "$container_name" \
  --memory=512m --cpus=1 --pids-limit=64 \
  --label "org.openai.codex.task=actions84-migration-$run_id" \
  --publish '127.0.0.1::5432/tcp' --env-file "$credential_file" "$IMAGE")
[[ -n "$container_id" ]]

published_port=$(docker_bounded 10 inspect --format '{{(index (index .NetworkSettings.Ports "5432/tcp") 0).HostPort}}' "$container_id")
[[ "$published_port" =~ ^[0-9]+$ ]]
reported_version=$(docker_bounded 10 exec "$container_id" postgres --version)
[[ "$reported_version" == *'17.11'* ]]

ready=0
for _ in $(seq 1 60); do
  if docker_bounded 5 exec "$container_id" pg_isready -q -U "$db_user" -d "$db_name"; then ready=1; break; fi
  sleep 1
done
[[ "$ready" -eq 1 ]]

database_url="postgresql://${db_user}:${db_password}@127.0.0.1:${published_port}/${db_name}"
export ACTIONS84_EVIDENCE_DIR="$evidence_dir"
export PYTHONPATH="$REPO/actions/src:$REPO/action_server/src"
export PYTHONDONTWRITEBYTECODE=1
export PYTHONNOUSERSITE=1
unset PYTHONHOME PYTHONUSERBASE
ulimit -f 2048
cd "$REPO/action_server"
"$ACTIONS84_PYTHON" --version >"$evidence_dir/interpreter-version.txt" 2>&1
chmod 600 "$evidence_dir/interpreter-version.txt"
set +e
ACTIONS_TEST_DATABASE_URL="$database_url" timeout --signal=TERM --kill-after=10 180 \
  "$ACTIONS84_PYTHON" "$HARNESS" >"$raw_test_log" 2>&1
test_status=$?
set -e
sanitize_file "$raw_test_log" "$evidence_dir/test.log"
[[ "$test_status" -eq 0 ]]

