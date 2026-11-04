#!/usr/bin/env bash
set -Eeuo pipefail

# Hosted, credential-free source wheel + real RCC vertical. The caller supplies
# an Ubuntu 24.04 runner with Python 3.12, uv, Poetry, and network access to
# public package/RCC sources. No repository or account credentials are passed
# to RCC.

repo_root="$(git rev-parse --show-toplevel)"
runner_temp="${RUNNER_TEMP:?RUNNER_TEMP is required}"
test -d "$runner_temp"
test ! -L "$runner_temp"
phase=preflight
status_file="$runner_temp/actions340-vertical-status.txt"
trap 'result=$?; printf "phase=%s\nexit_code=%s\n" "$phase" "$result" > "$status_file"' EXIT

retained_floor=10803773440
start_reserve=3045752832
free_bytes="$(df -PB1 "$runner_temp" | awk 'NR == 2 { print $4 }')"
[[ "$free_bytes" =~ ^[0-9]+$ ]]
if (( free_bytes < retained_floor + start_reserve )); then
  echo "insufficient free space: need retained floor plus two-home start reserve" >&2
  exit 1
fi

task_root="$(mktemp -d "$runner_temp/actions340-real-vertical.XXXXXXXX")"
chmod 700 "$task_root"
wheelhouse="$task_root/wheels"
mkdir -m 700 "$wheelhouse"

host_venv="$task_root/host-venv"
phase=host_environment
uv venv --seed --python 3.12 "$host_venv"

rcc_sha256=7e588c01751ca2ae15ba13ef67f2f4b7567697a5a8389737059a73936f509428
phase=pinned_rcc
rcc="$task_root/rcc"
curl --fail --location --silent --show-error --retry 2 --connect-timeout 15 --max-time 180 \
  https://github.com/joshyorko/rcc/releases/download/v18.19.3/rcc-linux64 \
  --output "$task_root/rcc.download"
printf '%s  %s\n' "$rcc_sha256" "$task_root/rcc.download" | sha256sum --check --status -
mv "$task_root/rcc.download" "$rcc"
chmod 700 "$rcc"
test "$("$rcc" --version)" = "v18.19.3"
runtime_rcc="$repo_root/action_server/src/actions/server/bin/rcc-18.19.3"
if [[ -e "$runtime_rcc" || -L "$runtime_rcc" ]]; then
  if [[ -L "$runtime_rcc" || ! -f "$runtime_rcc" || ! -x "$runtime_rcc" ]] ||
    ! printf '%s  %s\n' "$rcc_sha256" "$runtime_rcc" | sha256sum --check --status -; then
    echo "existing Action Server RCC must be a regular executable with the pinned hash" >&2
    exit 1
  fi
else
  mkdir -p "$(dirname "$runtime_rcc")"
  install -m 700 "$rcc" "$runtime_rcc"
fi
printf '%s  %s\n' "$rcc_sha256" "$runtime_rcc" | sha256sum --check --status -

cd "$repo_root/action_server"
phase=locked_dependencies
uvx --from poetry==2.1.1 --with poetry-plugin-export==1.9.0 poetry export \
  --with dev --format requirements.txt --output "$task_root/poetry-export.txt"
python3 - "$task_root/poetry-export.txt" "$task_root/locked-host-requirements.txt" "$repo_root" <<'PY'
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

source = Path(sys.argv[1]).read_text(encoding="utf-8").splitlines()
target = Path(sys.argv[2])
repo = Path(sys.argv[3]).resolve()
local_paths = {
    (repo / "actions").resolve(): "actions-core",
    (repo / "actions-http-helper").resolve(): "actions-http-helper",
    (repo / "devutils").resolve(): "actions-local-devutils",
    (repo / "work-items").resolve(): "actions-work-items",
}
result = []
seen = set()
for line in source:
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        continue
    if stripped.startswith("-e ") or "file://" in stripped or stripped.startswith(("../", "./")):
        requirement = stripped.split(";", 1)[0].strip()
        name, separator, uri = requirement.partition(" @ ")
        if not separator:
            name, uri = "", requirement.removeprefix("-e ").strip()
        parsed = urlsplit(uri)
        if parsed.scheme != "file" or parsed.netloc not in ("", "localhost"):
            raise SystemExit("unrecognized local dependency in Poetry export")
        path = Path(unquote(parsed.path)).resolve()
        expected = local_paths.get(path)
        if expected is None or (name and name.lower().replace("_", "-") != expected) or expected in seen:
            raise SystemExit("unexpected or duplicate local dependency in Poetry export")
        seen.add(expected)
        continue
    if (stripped.startswith("-") and not stripped.startswith("--hash=")) or " @ " in stripped:
        raise SystemExit("unsupported dependency option or direct URL in Poetry export")
    result.append(line)
if not result or seen != set(local_paths.values()):
    raise SystemExit("Poetry export did not contain the expected locked dependencies")
target.write_text("\n".join(result) + "\n", encoding="utf-8")
PY
uv pip install --python "$host_venv/bin/python" --no-deps --require-hashes \
  -r "$task_root/locked-host-requirements.txt"
"$host_venv/bin/python" scripts/build_oauth2_config.py

cd "$repo_root/actions-http-helper"
phase=build_wheels
uvx --from poetry==2.1.1 --with poetry-plugin-export==1.9.0 poetry build -f wheel -o "$wheelhouse"
cd "$repo_root/action_server"
ACTION_SERVER_SKIP_DOWNLOAD_IN_BUILD=1 uvx --from poetry==2.1.1 --with poetry-plugin-export==1.9.0 poetry build -f wheel -o "$wheelhouse"
cd "$repo_root/actions"
uvx --from poetry==2.1.1 --with poetry-plugin-export==1.9.0 poetry build -f wheel -o "$wheelhouse"
cd "$repo_root/work-items"
uvx --from poetry==2.1.1 --with poetry-plugin-export==1.9.0 poetry build -f wheel -o "$wheelhouse"

one_wheel() {
  python3 - "$wheelhouse" "$1" <<'PY'
import sys
from pathlib import Path
matches = sorted(Path(sys.argv[1]).glob(sys.argv[2]))
if len(matches) != 1 or not matches[0].is_file():
    raise SystemExit('exactly one wheel is required for ' + sys.argv[2])
print(matches[0])
PY
}
runtime_wheel="$(one_wheel 'actions_runtime-*.whl')"
core_wheel="$(one_wheel 'actions_core-*.whl')"
work_items_wheel="$(one_wheel 'actions_work_items-*.whl')"
helper_wheel="$(one_wheel 'actions_http_helper-*.whl')"
for wheel in "$runtime_wheel" "$core_wheel" "$work_items_wheel" "$helper_wheel"; do
  test -n "$wheel" && test -f "$wheel"
done
uv pip install --python "$host_venv/bin/python" --no-deps \
  "$runtime_wheel" "$core_wheel" "$work_items_wheel" "$helper_wheel"
uv pip check --python "$host_venv/bin/python"

core_version="$("$host_venv/bin/python" - "$core_wheel" <<'PY'
import sys, zipfile
from email.parser import Parser
with zipfile.ZipFile(sys.argv[1]) as wheel:
    metadata = next(name for name in wheel.namelist() if name.endswith('.dist-info/METADATA'))
    print(Parser().parsestr(wheel.read(metadata).decode()).get('Version'))
PY
)"
[[ "$core_version" =~ ^[A-Za-z0-9.!+_-]+$ ]]
cat > "$task_root/action-package.yaml" <<EOF
name: actions340-real-vertical-action
description: Actions 340 real child vertical Action
dependencies:
  conda-forge:
    - python=3.12.15
    - pip=24
  pypi:
    - actions-core=$core_version
EOF
cat > "$task_root/robot-package.yaml" <<'EOF'
name: actions340-real-vertical-robot
description: Actions 340 real child vertical Robot
dependencies:
  conda-forge:
    - python=3.12.15
    - pip=24
  pypi:
    - robotframework=7.4.2
EOF
chmod 600 "$task_root/action-package.yaml" "$task_root/robot-package.yaml"

core_hash="$(sha256sum "$core_wheel" | awk '{print $1}')"
runtime_hash="$(sha256sum "$runtime_wheel" | awk '{print $1}')"
work_items_hash="$(sha256sum "$work_items_wheel" | awk '{print $1}')"
source_tree="$(git -C "$repo_root" rev-parse 'HEAD^{tree}')"
source_commit="$(git -C "$repo_root" rev-parse HEAD)"
printf 'vertical_task_root=%s\nsource_commit=%s\nsource_tree=%s\n' "$task_root" "$source_commit" "$source_tree" | tee "$task_root/identity.txt"
for item in "$runtime_wheel" "$core_wheel" "$work_items_wheel" "$helper_wheel" "$rcc" \
  "$repo_root/action_server/poetry.lock" "$repo_root/action_server/src/actions/server/_oauth2_config.py" \
  "$task_root/action-package.yaml" "$task_root/robot-package.yaml"; do
  printf 'file=%s sha256=%s\n' "$(basename "$item")" "$(sha256sum "$item" | awk '{print $1}')" | tee -a "$task_root/identity.txt"
done
export ACTIONS_INTERNAL_CHILD_PREPARE_RCC=1
phase=prepare_rcc_artifacts
"$host_venv/bin/python" "$repo_root/developer/tests/prepare_internal_child_real_vertical_rcc.py" \
  --rcc "$rcc" --core-wheel "$core_wheel" \
  --action-manifest "$task_root/action-package.yaml" \
  --robot-manifest "$task_root/robot-package.yaml" \
  --output-dir "$task_root/preparation" \
  --minimum-free-bytes "$retained_floor"

action_receipt="$task_root/preparation/action/prepared-rcc.json"
robot_receipt="$task_root/preparation/robot/prepared-rcc.json"
for path in "$action_receipt" "$robot_receipt"; do test -f "$path"; done
mkdir -m 700 "$task_root/test-tmp"
mkdir -m 700 "$task_root/test-home" "$task_root/test-config" "$task_root/test-cache"

export ACTIONS_INTERNAL_CHILD_REAL_RCC=1
export ACTIONS_INTERNAL_CHILD_ACTION_RCC_RECEIPT="$action_receipt"
export ACTIONS_INTERNAL_CHILD_ROBOT_RCC_RECEIPT="$robot_receipt"
export ACTIONS_INTERNAL_CHILD_CORE_WHEEL="$core_wheel"
export ACTIONS_INTERNAL_CHILD_CORE_WHEEL_SHA256="$core_hash"
export ACTIONS_INTERNAL_CHILD_RUNTIME_WHEEL="$runtime_wheel"
export ACTIONS_INTERNAL_CHILD_RUNTIME_WHEEL_SHA256="$runtime_hash"
export ACTIONS_INTERNAL_CHILD_WORK_ITEMS_WHEEL="$work_items_wheel"
export ACTIONS_INTERNAL_CHILD_WORK_ITEMS_WHEEL_SHA256="$work_items_hash"
export ACTIONS_RUNTIME_RCC_BINARY="$rcc"
export PYTHONPATH="$repo_root/action_server/tests:$repo_root/devutils/src"
export TMPDIR="$task_root/test-tmp"
# Run pytest under the existing pidfd/subreaper supervisor so the retained
# disk floor is monitored throughout RCC execution and descendants are reaped.
cd "$repo_root/action_server"
phase=installed_vertical
"$host_venv/bin/python" - "$repo_root" "$runner_temp" "$retained_floor" "$task_root" <<'PY'
import importlib.util
import os
import sys
from pathlib import Path
from urllib.parse import urlsplit

repo = Path(sys.argv[1])
runner_temp = Path(sys.argv[2]).resolve(strict=True)
floor = int(sys.argv[3])
task_root = Path(sys.argv[4]).resolve(strict=True)
support_path = repo / "developer/tests/test_rcc_env_exec_fd_real.py"
spec = importlib.util.spec_from_file_location("vertical_ci_rcc_supervisor", support_path)
if spec is None or spec.loader is None:
    raise SystemExit("existing RCC subreaper support is unavailable")
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
allowed = (
    "ACTIONS_INTERNAL_CHILD_REAL_RCC",
    "ACTIONS_INTERNAL_CHILD_ACTION_RCC_RECEIPT",
    "ACTIONS_INTERNAL_CHILD_ROBOT_RCC_RECEIPT",
    "ACTIONS_INTERNAL_CHILD_CORE_WHEEL",
    "ACTIONS_INTERNAL_CHILD_CORE_WHEEL_SHA256",
    "ACTIONS_INTERNAL_CHILD_RUNTIME_WHEEL",
    "ACTIONS_INTERNAL_CHILD_RUNTIME_WHEEL_SHA256",
    "ACTIONS_INTERNAL_CHILD_WORK_ITEMS_WHEEL",
    "ACTIONS_INTERNAL_CHILD_WORK_ITEMS_WHEEL_SHA256",
    "ACTIONS_RUNTIME_RCC_BINARY",
    "PYTHONPATH",
    "TMPDIR",
)
test_env = {name: os.environ[name] for name in allowed}
test_env.update({
    "PATH": os.pathsep.join((str(task_root / "host-venv/bin"), "/usr/bin", "/bin")),
    "HOME": str(task_root / "test-home"),
    "XDG_CONFIG_HOME": str(task_root / "test-config"),
    "XDG_CACHE_HOME": str(task_root / "test-cache"),
    "LANG": "C.UTF-8",
    "LC_ALL": "C.UTF-8",
})
proxy_names = {"http_proxy", "https_proxy", "all_proxy", "no_proxy"}
ca_names = {"SSL_CERT_FILE", "SSL_CERT_DIR", "REQUESTS_CA_BUNDLE", "CURL_CA_BUNDLE"}
for name, value in os.environ.items():
    if name.lower() in proxy_names or name in ca_names:
        if name.lower() in proxy_names - {"no_proxy"}:
            parsed = urlsplit(value)
            if parsed.username is not None or parsed.password is not None:
                raise SystemExit("proxy credentials are not accepted")
        test_env[name] = value
junit_path = task_root / "junit.xml"
status, stdout, stderr = module._run_reaped(
    [sys.executable, "-m", "pytest", "-n", "0", "-vv",
     "tests/action_server_tests/test_internal_child_real_vertical.py::test_real_mcp_action_submits_detached_rcc_robot[sqlite]",
     "tests/action_server_tests/test_internal_child_real_vertical.py::test_real_child_live_cancellation_probe[sqlite]",
     "tests/action_server_tests/test_internal_child_real_vertical.py::test_real_failed_robot_is_not_automatically_retried_after_host_restart[sqlite]",
     "tests/action_server_tests/test_internal_child_real_vertical.py::test_real_crashed_robot_launch_requires_explicit_reconciliation[sqlite]",
     "tests/action_server_tests/test_managed_work_items_real_robot_vertical.py::test_model_enqueue_claim_rcc_and_authorized_outputs[sqlite]",
     f"--junitxml={junit_path}"],
    env=test_env,
    timeout=900,
    disk_paths=(runner_temp,),
    minimum_free_bytes=floor,
)
sys.stdout.buffer.write(stdout)
sys.stderr.buffer.write(stderr)
print(f"vertical_junit={junit_path}")
raise SystemExit(status)
PY
test -f "$task_root/junit.xml"
"$host_venv/bin/python" - "$task_root/junit.xml" <<'PY'
import sys
from xml.etree import ElementTree
root = ElementTree.parse(sys.argv[1]).getroot()
cases = root.findall('.//testcase')
expected = {
    'test_real_mcp_action_submits_detached_rcc_robot[sqlite]',
    'test_real_child_live_cancellation_probe[sqlite]',
    'test_real_failed_robot_is_not_automatically_retried_after_host_restart[sqlite]',
    'test_real_crashed_robot_launch_requires_explicit_reconciliation[sqlite]',
    'test_model_enqueue_claim_rcc_and_authorized_outputs[sqlite]',
}
if {case.get('name') for case in cases} != expected or len(cases) != len(expected) or any(
    case.find(tag) is not None for case in cases for tag in ('skipped', 'failure', 'error')
):
    raise SystemExit('all five SQLite vertical cases must execute and pass')
PY
printf 'VERTICAL_EVIDENCE_DIR=%s\nVERTICAL_JUNIT=%s\n' "$task_root" "$task_root/junit.xml"
phase=complete
