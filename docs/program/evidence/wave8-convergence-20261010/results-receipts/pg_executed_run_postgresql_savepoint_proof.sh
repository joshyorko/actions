#!/usr/bin/env bash
set -Eeuo pipefail
set +x
umask 077
unset ACTIONS_TEST_DATABASE_URL

readonly REPO='/workspace/work/actions-mk3-wave8-postgres'
readonly EXPECTED_HEAD='1421fcf85c1b681aef1fe58fe2902f776f208167'
readonly EXPECTED_TREE='42f70afb88877335a71e9bc02ad2e85730d69442'
readonly IMAGE='docker.io/library/postgres@sha256:aa90e97ee862e558111d34cfb8b2c4bec768c2b039fb791341686928560263b3'
readonly EXPECTED_IMAGE_DIGEST='postgres@sha256:aa90e97ee862e558111d34cfb8b2c4bec768c2b039fb791341686928560263b3'
readonly PYTHON_EXPECTED='/workspace/work/actions-mk3-pr302/action_server/.venv/bin/python'
readonly TEST_SCRIPT='/workspace/work/actions-mk3-evidence/database-savepoint/postgresql-savepoint-proof-20261010T2320Z/probe_failed_savepoint_postgresql.py'
readonly EVIDENCE_BASE='/workspace/work/actions-mk3-evidence/database-savepoint/postgresql-savepoint-proof-20261010T2320Z'
readonly RCC='/workspace/actions-cloud/bin/rcc'

if [[ -z "${ACTIONS_SAVEPOINT_PYTHON:-}" || "$ACTIONS_SAVEPOINT_PYTHON" != "$PYTHON_EXPECTED" || ! -x "$ACTIONS_SAVEPOINT_PYTHON" ]]; then
  echo 'ACTIONS_SAVEPOINT_PYTHON must name the existing reviewed RCC-prepared interpreter' >&2
  exit 2
fi
for tool in docker timeout python3 sha256sum; do command -v "$tool" >/dev/null; done

cd "$REPO"
actual_head=$(git rev-parse HEAD)
actual_tree=$(git rev-parse 'HEAD^{tree}')
[[ "$actual_head" == "$EXPECTED_HEAD" && "$actual_tree" == "$EXPECTED_TREE" ]]
[[ -z "$(git status --porcelain)" ]]

run_id="$(date -u +%Y%m%dT%H%M%SZ)-$$"
evidence_dir="$EVIDENCE_BASE/execution-$run_id"
mkdir -m 700 "$evidence_dir"
container_name="actions-db-savepoint-$run_id"
container_id=''
credential_file=''
database_url=''
db_password=''
db_user='actions_savepoint'
db_name='savepoint_probe'
published_port=''
image_id=''
image_platform=''
container_limits=''
repo_digests=''
postgres_version=''
rcc_version=''
preflight_status='NOT_RUN'
test_status='NOT_RUN'
test_exit_code=''
test_pid=''
container_cleanup='NOT_ATTEMPTED'
credential_cleanup='NOT_CREATED'
server_log_status='NOT_CAPTURED'
test_log_status='NOT_CAPTURED'
cleanup_failed=0
raw_server_log="$evidence_dir/.postgres.raw"
raw_test_log="$evidence_dir/.test.raw"

bounded_docker() {
  local seconds="$1"; shift
  timeout --signal=TERM --kill-after=5 "$seconds" docker "$@"
}

sanitize_file() {
  local raw="$1" out="$2"
  SANITIZE_RAW="$raw" SANITIZE_OUT="$out" SANITIZE_DATABASE_URL="${database_url:-}" SANITIZE_PASSWORD="${db_password:-}" python3 - <<'PY'
import os
from pathlib import Path
raw = Path(os.environ['SANITIZE_RAW']).read_text(errors='replace')
for secret in (os.environ.get('SANITIZE_DATABASE_URL', ''), os.environ.get('SANITIZE_PASSWORD', '')):
    if secret:
        raw = raw.replace(secret, '[REDACTED]')
Path(os.environ['SANITIZE_OUT']).write_text(raw[:1048576] + ('\n[TRUNCATED]\n' if len(raw) > 1048576 else ''))
os.chmod(os.environ['SANITIZE_OUT'], 0o600)
PY
}

write_receipt() {
  export SAVEPOINT_EVIDENCE_DIR="$evidence_dir" SAVEPOINT_HEAD="$actual_head" SAVEPOINT_TREE="$actual_tree"
  export SAVEPOINT_CONTAINER_NAME="$container_name" SAVEPOINT_CONTAINER_ID="$container_id"
  export SAVEPOINT_IMAGE="$IMAGE" SAVEPOINT_IMAGE_ID="$image_id" SAVEPOINT_IMAGE_PLATFORM="$image_platform"
  export SAVEPOINT_CONTAINER_LIMITS="$container_limits"
  export SAVEPOINT_REPO_DIGESTS="$repo_digests" SAVEPOINT_POSTGRES_VERSION="$postgres_version"
  export SAVEPOINT_PORT="$published_port" SAVEPOINT_TEST_STATUS="$test_status" SAVEPOINT_TEST_EXIT="$test_exit_code"
  export SAVEPOINT_TEST_PID="$test_pid" SAVEPOINT_PREFLIGHT_STATUS="$preflight_status"
  export SAVEPOINT_CONTAINER_CLEANUP="$container_cleanup" SAVEPOINT_CREDENTIAL_CLEANUP="$credential_cleanup"
  export SAVEPOINT_SERVER_LOG_STATUS="$server_log_status" SAVEPOINT_TEST_LOG_STATUS="$test_log_status"
  export SAVEPOINT_RCC_VERSION="$rcc_version" SAVEPOINT_PYTHON="$ACTIONS_SAVEPOINT_PYTHON"
  export SAVEPOINT_RUN_ID="$run_id" SAVEPOINT_INVOKED_FROM_RCC='true'
  env -u ACTIONS_TEST_DATABASE_URL python3 - <<'PY'
import hashlib, json, os, pathlib, subprocess
root=pathlib.Path(os.environ['SAVEPOINT_EVIDENCE_DIR'])
repo=pathlib.Path('/workspace/work/actions-mk3-wave8-postgres')
items={}
for name,path in {
 'test.log':root/'test.log',
 'postgres.log':root/'postgres.log',
 'preflight.json':root/'preflight.json',
 'probe-result.json':root/'probe-result.json',
 'interpreter-version.txt':root/'interpreter-version.txt',
 'image-inspect.txt':root/'image-inspect.txt',
 'rcc-version.txt':root/'rcc-version.txt',
}.items():
 if path.is_file(): items[name]={'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
source_files={}
for rel in ('action_server/src/actions/server/_database.py','action_server/tests/action_server_tests/test_database.py','docs/skills/repository-operations.md'):
 p=repo/rel
 source_files[rel]={'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
files={}
for rel in ('probe_failed_savepoint_postgresql.py','run_postgresql_savepoint_proof.sh'):
 p=pathlib.Path('/workspace/work/actions-mk3-evidence/database-savepoint/postgresql-savepoint-proof-20261010T2320Z')/rel
 files[rel]={'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
manifest={
 'observed_at_utc':os.environ['SAVEPOINT_RUN_ID'],
 'source':{'head':os.environ['SAVEPOINT_HEAD'],'tree':os.environ['SAVEPOINT_TREE'],'clean':True,'files':source_files},
 'toolchain':{'canonical_rcc':os.environ['SAVEPOINT_RCC_VERSION'],'rcc_executable_sha256':hashlib.sha256(pathlib.Path('/workspace/actions-cloud/bin/rcc').read_bytes()).hexdigest(),'prepared_python':os.environ['SAVEPOINT_PYTHON'],'gateway_entered':os.environ['SAVEPOINT_INVOKED_FROM_RCC']=='true'},
 'service':{'image':os.environ['SAVEPOINT_IMAGE'],'repo_digests':os.environ['SAVEPOINT_REPO_DIGESTS'],'image_id':os.environ['SAVEPOINT_IMAGE_ID'],'platform':os.environ['SAVEPOINT_IMAGE_PLATFORM'],'postgres_version':os.environ['SAVEPOINT_POSTGRES_VERSION'],'container_name':os.environ['SAVEPOINT_CONTAINER_NAME'],'container_id':os.environ['SAVEPOINT_CONTAINER_ID'],'loopback_port':os.environ['SAVEPOINT_PORT'],'requested_limits':{'memory':'512m','cpu':1,'pids':64},'observed_limits':os.environ['SAVEPOINT_CONTAINER_LIMITS']},
 'result':{'preflight':os.environ['SAVEPOINT_PREFLIGHT_STATUS'],'test_status':os.environ['SAVEPOINT_TEST_STATUS'],'test_exit_code':os.environ['SAVEPOINT_TEST_EXIT'] or None,'test_process_pid':os.environ['SAVEPOINT_TEST_PID'] or None,'container_cleanup':os.environ['SAVEPOINT_CONTAINER_CLEANUP'],'credential_cleanup':os.environ['SAVEPOINT_CREDENTIAL_CLEANUP'],'server_log_status':os.environ['SAVEPOINT_SERVER_LOG_STATUS'],'test_log_status':os.environ['SAVEPOINT_TEST_LOG_STATUS']},
 'executed_files':files,'artifacts':items,
 'invocation':'source /workspace/actions-cloud/activate.sh && ACTIONS_SAVEPOINT_PYTHON=/workspace/work/actions-mk3-pr302/action_server/.venv/bin/python /workspace/actions-cloud/bin/rcc task script -r developer/toolkit.yaml --no-build -- bash <this wrapper>',
 'limitations':['One in-process production Database transaction path on PostgreSQL 17.11; no migration, full CLI/server, concurrency, wheel, frozen, native, or release claim.','The test deliberately aborts an outer PostgreSQL transaction with division by zero; a nested SAVEPOINT then fails with SQLSTATE 25P02. This validates application cleanup after that actual server error, not a server privilege that denies SAVEPOINT in a healthy transaction.']
}
(root/'attempt-manifest.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
PY
  chmod 600 "$evidence_dir/attempt-manifest.json"
}

cleanup() {
  local original_status=$?
  local found_owner='' found_name='' found_ids='' found_id='' remaining=''
  set +e
  if [[ -n "$container_id" ]]; then
    found_owner=$(bounded_docker 10 container inspect --format '{{index .Config.Labels "org.openai.codex.task"}}' "$container_id" 2>/dev/null)
    found_name=$(bounded_docker 10 container inspect --format '{{.Name}}' "$container_id" 2>/dev/null)
    if [[ "$found_owner" == "$container_name" && "$found_name" == "/$container_name" ]]; then
      if bounded_docker 10 logs "$container_id" >"$raw_server_log" 2>&1; then
        if sanitize_file "$raw_server_log" "$evidence_dir/postgres.log"; then server_log_status='CAPTURED_SANITIZED'; else server_log_status='SANITIZE_FAILED'; cleanup_failed=1; fi
      else server_log_status='CAPTURE_FAILED'; cleanup_failed=1; fi
      bounded_docker 20 rm -f "$container_id" >/dev/null 2>&1
      remaining=$(bounded_docker 10 container ls --all --quiet --filter "id=$container_id" 2>/dev/null)
      if [[ -z "$remaining" ]]; then container_cleanup='REMOVED_AND_VERIFIED_ABSENT'; else container_cleanup='REMOVE_FAILED_PRESENT'; cleanup_failed=1; fi
    else
      container_cleanup='OWNERSHIP_UNVERIFIED_LEFT_UNTOUCHED'; cleanup_failed=1
    fi
  else
    found_ids=$(bounded_docker 10 container ls --all --quiet --filter "name=^/${container_name}$" 2>/dev/null)
    if [[ -z "$found_ids" ]]; then
      container_cleanup='NO_CONTAINER_CREATED'
    else
      found_id=$(printf '%s\n' "$found_ids" | head -n 1)
      found_owner=$(bounded_docker 10 container inspect --format '{{index .Config.Labels "org.openai.codex.task"}}' "$found_id" 2>/dev/null)
      found_name=$(bounded_docker 10 container inspect --format '{{.Name}}' "$found_id" 2>/dev/null)
      if [[ "$found_owner" == "$container_name" && "$found_name" == "/$container_name" ]]; then
        container_id="$found_id"
        if bounded_docker 10 logs "$container_id" >"$raw_server_log" 2>&1; then
          if sanitize_file "$raw_server_log" "$evidence_dir/postgres.log"; then server_log_status='CAPTURED_SANITIZED'; else server_log_status='SANITIZE_FAILED'; cleanup_failed=1; fi
        else server_log_status='CAPTURE_FAILED'; cleanup_failed=1; fi
        bounded_docker 20 rm -f "$container_id" >/dev/null 2>&1
        remaining=$(bounded_docker 10 container ls --all --quiet --filter "id=$container_id" 2>/dev/null)
        if [[ -z "$remaining" ]]; then container_cleanup='REMOVED_AND_VERIFIED_ABSENT'; else container_cleanup='REMOVE_FAILED_PRESENT'; cleanup_failed=1; fi
      else
        container_cleanup='NAME_MATCH_IDENTITY_UNVERIFIED_LEFT_UNTOUCHED'; cleanup_failed=1
      fi
    fi
  fi
  if [[ -n "$credential_file" ]]; then
    rm -f -- "$credential_file"
    if [[ ! -e "$credential_file" ]]; then credential_cleanup='REMOVED_AND_VERIFIED_ABSENT'; else credential_cleanup='REMOVE_FAILED'; cleanup_failed=1; fi
  fi
  if [[ -f "$raw_test_log" ]]; then
    if sanitize_file "$raw_test_log" "$evidence_dir/test.log"; then test_log_status='CAPTURED_SANITIZED'; else test_log_status='SANITIZE_FAILED'; cleanup_failed=1; fi
  fi
  if [[ -n "$evidence_dir" && -d "$evidence_dir" ]]; then
    write_receipt || cleanup_failed=1
  fi
  if [[ $cleanup_failed -ne 0 && $original_status -eq 0 ]]; then original_status=125; fi
  exit "$original_status"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

sha256sum "$TEST_SCRIPT" "$0" >"$evidence_dir/runner-hashes.txt"
chmod 600 "$evidence_dir/runner-hashes.txt"
"$RCC" --version >"$evidence_dir/rcc-version.txt" 2>&1
rcc_version=$(cat "$evidence_dir/rcc-version.txt")
[[ "$rcc_version" == *'18.19.3'* ]]

export SAVEPOINT_PREFLIGHT_REPO="$REPO" SAVEPOINT_PREFLIGHT_PYTHON="$ACTIONS_SAVEPOINT_PYTHON"
PYTHONPATH="$REPO/actions/src:$REPO/action_server/src" PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 \
  env -u PYTHONHOME -u PYTHONUSERBASE "$ACTIONS_SAVEPOINT_PYTHON" - <<'PY' >"$evidence_dir/preflight.json"
import hashlib, importlib.metadata, json, os, sys
from pathlib import Path
root=Path(os.environ['SAVEPOINT_PREFLIGHT_REPO']).resolve()
sys.path[:0]=[str(root/'actions/src'),str(root/'action_server/src')]
import psycopg
import actions.server._database as db
origin=Path(db.__file__).resolve()
expected=root/'action_server/src/actions/server/_database.py'
if origin != expected: raise SystemExit('Database module origin mismatch')
if psycopg.__version__ != '3.3.4': raise SystemExit('unexpected psycopg version')
payload={'sys_executable':sys.executable,'python_version':sys.version.split()[0],'psycopg_version':psycopg.__version__,'database_module':str(origin),'database_sha256':hashlib.sha256(origin.read_bytes()).hexdigest(),'runtime_distribution':importlib.metadata.version('actions-runtime')}
print(json.dumps(payload,indent=2,sort_keys=True))
PY
chmod 600 "$evidence_dir/preflight.json"
preflight_status='PASS'

repo_digests=$(bounded_docker 10 image inspect --format '{{json .RepoDigests}}' "$IMAGE")
[[ "$repo_digests" == *"$EXPECTED_IMAGE_DIGEST"* ]]
image_id=$(bounded_docker 10 image inspect --format '{{.Id}}' "$IMAGE")
image_platform=$(bounded_docker 10 image inspect --format '{{.Os}}/{{.Architecture}}' "$IMAGE")
[[ "$image_platform" == 'linux/amd64' ]]
printf 'image_id=%s\nrepo_digests=%s\nplatform=%s\n' "$image_id" "$repo_digests" "$image_platform" >"$evidence_dir/image-inspect.txt"
chmod 600 "$evidence_dir/image-inspect.txt"

if [[ -n "$(bounded_docker 10 container ls --all --quiet --filter "name=^/${container_name}$")" ]]; then
  echo 'unique container name already exists; refusing to reuse' >&2
  exit 2
fi
credential_file=$(mktemp "$evidence_dir/.postgres-credentials.XXXXXX")
chmod 600 "$credential_file"
db_password=$(od -An -N24 -tx1 /dev/urandom | tr -d ' \n')
[[ ${#db_password} -eq 48 ]]
printf 'POSTGRES_USER=%s\nPOSTGRES_PASSWORD=%s\nPOSTGRES_DB=%s\n' "$db_user" "$db_password" "$db_name" >"$credential_file"

container_id=$(bounded_docker 20 run --detach --name "$container_name" \
  --label "org.openai.codex.task=$container_name" \
  --memory=512m --cpus=1 --pids-limit=64 \
  --publish '127.0.0.1::5432/tcp' --env-file "$credential_file" "$IMAGE")
[[ "$container_id" =~ ^[0-9a-f]{64}$ ]]
container_limits=$(bounded_docker 10 inspect --format '{{.HostConfig.Memory}} {{.HostConfig.NanoCpus}} {{.HostConfig.PidsLimit}}' "$container_id")
[[ "$container_limits" == '536870912 1000000000 64' ]]
published_port=$(bounded_docker 10 inspect --format '{{(index (index .NetworkSettings.Ports "5432/tcp") 0).HostPort}}' "$container_id")
[[ "$published_port" =~ ^[0-9]+$ ]]
postgres_version=$(bounded_docker 10 exec "$container_id" postgres --version)
[[ "$postgres_version" == *'17.11'* ]]
ready=0
for _ in $(seq 1 45); do
  if bounded_docker 5 exec "$container_id" pg_isready -q -U "$db_user" -d "$db_name"; then ready=1; break; fi
  sleep 1
done
[[ "$ready" -eq 1 ]]

database_url="postgresql://${db_user}:${db_password}@127.0.0.1:${published_port}/${db_name}"
export PYTHONPATH="$REPO/actions/src:$REPO/action_server/src" PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1
unset PYTHONHOME PYTHONUSERBASE
ulimit -f 2048
"$ACTIONS_SAVEPOINT_PYTHON" --version >"$evidence_dir/interpreter-version.txt" 2>&1
chmod 600 "$evidence_dir/interpreter-version.txt"
set +e
ACTIONS_TEST_DATABASE_URL="$database_url" ACTIONS_SAVEPOINT_RECEIPT="$evidence_dir/probe-result.json" \
  timeout --signal=TERM --kill-after=5 60 "$ACTIONS_SAVEPOINT_PYTHON" "$TEST_SCRIPT" >"$raw_test_log" 2>&1
test_exit_code=$?
set -e
if [[ -f "$evidence_dir/probe-result.json" ]]; then test_pid=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("python_pid", ""))' "$evidence_dir/probe-result.json" 2>/dev/null || true); fi
if [[ "$test_exit_code" -eq 0 ]]; then test_status='PASS'; else test_status='FAIL'; fi
[[ "$test_status" == 'PASS' ]]
