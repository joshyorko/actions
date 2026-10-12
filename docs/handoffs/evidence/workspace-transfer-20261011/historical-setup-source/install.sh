#!/usr/bin/env bash
set -Eeuo pipefail
# RCC owns the outer toolchain. Poetry owns all five locked package environments.
# Run with permission for micromamba's standard ~/.conda registry and workspace skill links.
repo=/workspace/actions
state=/workspace/actions-cloud
[[ $(uname -s):$(uname -m) == Linux:x86_64 ]]
test -f "$repo/developer/toolkit.yaml"
mkdir -p "$state/bin" "$state/cache" "$state/config" "$state/logs"
cat > "$state/activate.sh" <<'ACTIVATION'
export ACTIONS_CLOUD_ROOT=/workspace/actions-cloud
export PATH="$ACTIONS_CLOUD_ROOT/bin:$PATH"
export ROBOCORP_HOME="$ACTIONS_CLOUD_ROOT/robocorp"
export XDG_CACHE_HOME="$ACTIONS_CLOUD_ROOT/cache"
export XDG_CONFIG_HOME="$ACTIONS_CLOUD_ROOT/config"
export POETRY_CACHE_DIR="$ACTIONS_CLOUD_ROOT/cache/pypoetry"
export POETRY_CONFIG_DIR="$ACTIONS_CLOUD_ROOT/config/pypoetry"
export UV_CACHE_DIR="$ACTIONS_CLOUD_ROOT/cache/uv"
export npm_config_cache="$ACTIONS_CLOUD_ROOT/cache/npm"
export GOCACHE="$ACTIONS_CLOUD_ROOT/cache/go-build"
export GOPATH="$ACTIONS_CLOUD_ROOT/cache/go"
export PLAYWRIGHT_BROWSERS_PATH="$ACTIONS_CLOUD_ROOT/cache/playwright"
export PYTEST_XDIST_AUTO_NUM_WORKERS=2
export POETRY_NO_INTERACTION=1
export BUILDX_CONFIG="$ACTIONS_CLOUD_ROOT/cache/buildx"
export ACTIONS_HOME="$ACTIONS_CLOUD_ROOT/actions-home"
export ROBOTS_HOME="$ACTIONS_CLOUD_ROOT/robots-home"
export GOMAXPROCS=2
export ACTIONS_RUNTIME_TEST_PYTHON=/workspace/actions/action_server/.venv/bin/python
ACTIVATION
source "$state/activate.sh"
mkdir -p "$state/actions-home"
if [[ ! -e "$HOME/.actions" && ! -L "$HOME/.actions" ]]; then
  ln -s "$state/actions-home" "$HOME/.actions"
fi
# Historical Action Server compatibility tests use the former wrapper home.
mkdir -p "$state/legacy-sema4ai"
if [[ ! -e "$HOME/.sema4ai" && ! -L "$HOME/.sema4ai" ]]; then
  ln -s "$state/legacy-sema4ai" "$HOME/.sema4ai"
fi
# An absent registry is linked to writable state; existing user registries are preserved.
mkdir -p "$state/conda-registry"
if [[ ! -e "$HOME/.conda" && ! -L "$HOME/.conda" ]]; then
  ln -s "$state/conda-registry" "$HOME/.conda"
fi
cat > "$state/configure-network.py" <<'NETWORK_PROFILE'
"""Refresh only the cloud-owned Actions HTTP profile from injected proxy settings."""
import json
import os
from pathlib import Path
import tempfile

path = Path.home() / '.actions/network-settings.yaml'
if path.exists():
    try:
        existing = json.loads(path.read_text())
    except (ValueError, OSError):
        print('Preserving existing user network profile.')
        raise SystemExit(0)
    if existing.get('current-profile') != 'codex-cloud' or len(existing.get('profiles', [])) != 1:
        print('Preserving existing user network profile.')
        raise SystemExit(0)
    profile = existing['profiles'][0]
    if profile.get('name') != 'codex-cloud' or set(profile) - {'name', 'proxy-settings'}:
        print('Preserving existing user network profile.')
        raise SystemExit(0)
proxy = {key: os.environ[name] for key, name in (
    ('http-proxy', 'HTTP_PROXY'), ('https-proxy', 'HTTPS_PROXY'), ('no-proxy', 'NO_PROXY')
) if os.environ.get(name)}
data = {'current-profile': 'codex-cloud', 'profiles': [{'name': 'codex-cloud', 'proxy-settings': proxy}]}
path.parent.mkdir(parents=True, exist_ok=True)
with tempfile.NamedTemporaryFile('w', dir=path.parent, delete=False) as stream:
    json.dump(data, stream, indent=2)
    stream.write('\n')
    temporary = Path(stream.name)
try:
    os.chmod(temporary, 0o600)
    temporary.replace(path)
finally:
    temporary.unlink(missing_ok=True)
print('Actions HTTP cloud proxy profile refreshed; TLS verification remains enabled.')
NETWORK_PROFILE
python3 "$state/configure-network.py"
expected=7e588c01751ca2ae15ba13ef67f2f4b7567697a5a8389737059a73936f509428
if [[ ! -e "$state/bin/rcc" ]]; then
  temporary=$(mktemp "$state/bin/rcc.XXXXXX")
  trap 'rm -f -- "$temporary"' EXIT
  curl --fail --location --retry 3 --silent --show-error     https://github.com/joshyorko/rcc/releases/download/v18.19.3/rcc-linux64 -o "$temporary"
  printf '%s  %s\n' "$expected" "$temporary" | sha256sum --check --status
  chmod +x "$temporary"
  mv "$temporary" "$state/bin/rcc"
  trap - EXIT
fi
printf '%s  %s\n' "$expected" "$state/bin/rcc" | sha256sum --check --status
[[ $(rcc version) == v18.19.3 ]]
cat > "$state/package-command.py" <<'PACKAGE_COMMAND'
"""Run package-local Poetry through the repository's RCC environment boundary."""
import importlib.util
import sys
from pathlib import Path

root = Path('/workspace/actions')
spec = importlib.util.spec_from_file_location('actions_toolkit', root / 'developer/toolkit.py')
toolkit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(toolkit)
package, *arguments = sys.argv[1:]
if package not in toolkit.PACKAGES or not arguments:
    raise SystemExit('usage: package-command.py PACKAGE POETRY_ARGUMENTS...')
toolkit.poetry(package, *arguments)
PACKAGE_COMMAND
# Keep specialist guidance pinned and outside the application checkout.
plugin_commit=5c20e80cc136a982949b516b1672bb331da6de7b
if [[ ! -f "$state/guidance/.source-commit" ]]; then
  temporary=$(mktemp -d)
  trap 'rm -rf -- "$temporary"' EXIT
  git -C "$temporary" init -q
  git -C "$temporary" remote add origin https://github.com/joshyorko/plugins
  git -C "$temporary" fetch --depth 1 origin "$plugin_commit"
  mkdir -p "$state/guidance"
  git -C "$temporary" archive FETCH_HEAD plugins/rcc | tar -x -C "$state/guidance"
  printf '%s\n' "$plugin_commit" > "$state/guidance/.source-commit"
  rm -rf -- "$temporary"
  trap - EXIT
fi
[[ $(cat "$state/guidance/.source-commit") == "$plugin_commit" ]]
mkdir -p /workspace/.agents/skills
for skill_dir in "$state"/guidance/plugins/rcc/skills/*; do
  [[ -f "$skill_dir/SKILL.md" ]] || continue
  skill_link=/workspace/.agents/skills/$(basename "$skill_dir")
  if [[ -e "$skill_link" || -L "$skill_link" ]]; then
    [[ $(readlink -f "$skill_link") == "$skill_dir" ]]
  else
    ln -s "$skill_dir" "$skill_link"
  fi
done
cd "$repo"
rcc robot diagnostics -r developer/toolkit.yaml --json
rcc run -r developer/toolkit.yaml --dev -t Doctor
# The package build supports a preseeded RCC, avoiding an unchecked duplicate download.
bundled_rcc="$repo/action_server/src/actions/server/bin/rcc-18.19.3"
mkdir -p "$(dirname "$bundled_rcc")"
if [[ ! -e "$bundled_rcc" ]]; then
  install -m 755 "$state/bin/rcc" "$bundled_rcc"
fi
printf '%s  %s\n' "$expected" "$bundled_rcc" | sha256sum --check --status
ACTION_SERVER_SKIP_DOWNLOAD_IN_BUILD=1 rcc run -r developer/toolkit.yaml --dev -t Bootstrap
rcc task script -r developer/toolkit.yaml -- python "$state/package-command.py" work-items sync --all-extras --no-interaction
rcc task script -r developer/toolkit.yaml -- python -c 'import toolkit; toolkit.run(["npm", "ci", "--no-audit", "--no-fund"], toolkit.REPOSITORY_ROOT / "action_server/frontend")'
rcc task script -r developer/toolkit.yaml -- python -c 'import toolkit; toolkit.run(["npx", "--no-install", "playwright", "install", "chromium"], toolkit.REPOSITORY_ROOT / "action_server/frontend")'
for package in actions actions-http-helper devutils work-items action_server; do
  test -x "$package/.venv/bin/python"
  "$package/.venv/bin/python" -c 'import sys; assert sys.prefix != sys.base_prefix; print(sys.executable)'
done
rcc run -r developer/toolkit.yaml --dev -t ToolkitTest
# Optional service/native/browser gates are run on demand using the saved start skill.

# A source CLI launcher is replaced only by an explicitly requested native build.
if [[ ! -e "$state/bin/action-server" ]]; then
  cat > "$state/bin/action-server" <<'SOURCE_CLI'
#!/usr/bin/env bash
exec /workspace/actions/action_server/.venv/bin/action-server "$@"
SOURCE_CLI
  chmod +x "$state/bin/action-server"
fi
