# Install Community Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace `BuildCommunity` with a cross-platform `InstallCommunity` task that builds, validates, atomically installs, and verifies the community Action Server at the executable location selected by `PATH`.

**Architecture:** Keep build orchestration in `developer/toolkit.py` and add small pure helpers for target resolution and atomic replacement so behavior is unit-testable. Existing PATH targets are replaced; otherwise a platform user-local bin directory is accepted only when it is already represented in PATH. The task performs smoke checks before and after replacement and never elevates privileges.

**Tech Stack:** Python 3.12, pathlib, shutil, tempfile, os.replace, pytest/unittest.mock, RCC toolkit YAML.

## Global Constraints

- Rename `BuildCommunity` and `build-community` to `InstallCommunity` and `install-community`; retain no compatibility alias.
- Preserve the current frontend build, Go-wrapped executable build with version `community-local`, and pre-install `new --help` smoke test.
- Resolve an existing target with `shutil.which("action-server")` (or `action-server.exe` on Windows).
- If no executable resolves, select the platform user-local bin directory and require its resolved directory to occur in PATH.
- Install through a temporary file in the target directory followed by `os.replace`; never expose a partial binary.
- Preserve POSIX executable permissions and never invoke sudo or another privilege-elevation mechanism.
- Verify the installed target with `version` and `new --help`.
- Preserve unrelated user changes, including `.plugin-dev/`.

---

### Task 1: Target Resolution and Atomic Installation

**Files:**
- Modify: `developer/toolkit.py`
- Test: `developer/tests/test_toolkit_contract.py`

**Interfaces:**
- Produces: `community_executable_name() -> str`
- Produces: `resolve_install_target(path_value: str | None = None) -> Path`
- Produces: `install_executable(source: Path, target: Path) -> None`

- [ ] **Step 1: Add failing target-resolution tests**

Add tests that patch `toolkit.shutil.which`, `toolkit.sys.platform`, `toolkit.Path.home`, and PATH as needed, then assert:

```python
assert toolkit.resolve_install_target() == Path("/home/linuxbrew/.linuxbrew/bin/action-server")
```

for an existing resolved executable; assert the POSIX fallback is `Path.home() / ".local/bin/action-server"`; assert Windows fallback is `Path(os.environ["LOCALAPPDATA"]) / "Programs/Actions/bin/action-server.exe"`; and assert a fallback directory absent from PATH raises `SystemExit` containing that directory.

- [ ] **Step 2: Run the focused tests and confirm failure**

Run: `python -m pytest developer/tests/test_toolkit_contract.py -k 'install_target' -v`

Expected: FAIL because `resolve_install_target` does not exist.

- [ ] **Step 3: Implement target resolution**

Implement exact platform naming and normalized PATH membership:

```python
def community_executable_name() -> str:
    return "action-server.exe" if sys.platform == "win32" else "action-server"


def resolve_install_target(path_value: str | None = None) -> Path:
    executable = community_executable_name()
    resolved = shutil.which(executable, path=path_value)
    if resolved:
        return Path(resolved).resolve()
    if sys.platform == "win32":
        local_app_data = os.environ.get("LOCALAPPDATA")
        if not local_app_data:
            raise SystemExit("LOCALAPPDATA is required to install Action Server")
        directory = Path(local_app_data) / "Programs" / "Actions" / "bin"
    else:
        directory = Path.home() / ".local" / "bin"
    entries = [Path(entry).resolve() for entry in (path_value or os.environ.get("PATH", "")).split(os.pathsep) if entry]
    if directory.resolve() not in entries:
        raise SystemExit(f"Install directory is not on PATH: {directory}")
    return directory / executable
```

- [ ] **Step 4: Add failing atomic-install tests**

Use `tmp_path` to create an old target and new source. Assert successful replacement has the source bytes, retains executable mode on POSIX, and leaves no temporary sibling. Patch `toolkit.os.replace` to raise `PermissionError` and assert the old target bytes remain and the exception message identifies the target.

- [ ] **Step 5: Run atomic-install tests and confirm failure**

Run: `python -m pytest developer/tests/test_toolkit_contract.py -k 'install_executable' -v`

Expected: FAIL because `install_executable` does not exist.

- [ ] **Step 6: Implement atomic replacement**

Use `tempfile.NamedTemporaryFile(dir=target.parent, prefix=f".{target.name}.", delete=False)`, close it, copy with `shutil.copy2`, ensure POSIX execute bits with `temp_path.chmod(temp_path.stat().st_mode | 0o111)`, then call `os.replace(temp_path, target)`. On failure, unlink only the known temporary path and raise `SystemExit(f"Unable to install Action Server at {target}: {error}")`.

- [ ] **Step 7: Run focused tests**

Run: `python -m pytest developer/tests/test_toolkit_contract.py -k 'install_target or install_executable' -v`

Expected: PASS.

- [ ] **Step 8: Commit the helper contract**

```bash
git add developer/toolkit.py developer/tests/test_toolkit_contract.py
git commit -m "feat: add atomic community installer"
```

### Task 2: InstallCommunity Task Wiring

**Files:**
- Modify: `developer/toolkit.py`
- Modify: `developer/toolkit.yaml`
- Test: `developer/tests/test_toolkit_contract.py`

**Interfaces:**
- Consumes: `resolve_install_target() -> Path`
- Consumes: `install_executable(source: Path, target: Path) -> None`
- Produces: `install_community() -> None`

- [ ] **Step 1: Replace the dispatcher contract test with a failing install contract**

Patch `toolkit.poetry`, `toolkit.run`, `toolkit.resolve_install_target`, and `toolkit.install_executable`. Assert the two existing Poetry build calls remain, followed by pre-install `new --help`, installation from `action_server/dist/final/<executable>` to the resolved target, installed `version`, and installed `new --help`.

- [ ] **Step 2: Run the contract test and confirm failure**

Run: `python -m pytest developer/tests/test_toolkit_contract.py::test_install_community_builds_installs_and_verifies -v`

Expected: FAIL because `install_community` does not exist.

- [ ] **Step 3: Implement `install_community` and rename the CLI command**

Rename `build_community` to `install_community`. Retain both build calls and the source smoke check, resolve the target, call `install_executable`, then run `[str(target), "version"]` and `[str(target), "new", "--help"]`. Replace the `COMMANDS` key with `"install-community"`.

- [ ] **Step 4: Rename the RCC task**

In `developer/toolkit.yaml`, replace:

```yaml
  BuildCommunity:
    shell: python toolkit.py build-community
```

with:

```yaml
  InstallCommunity:
    shell: python toolkit.py install-community
```

- [ ] **Step 5: Update static task-name assertions**

Change expected task sets and workflow command assertions in `developer/tests/test_toolkit_contract.py` from `BuildCommunity` to `InstallCommunity` and from `build-community` to `install-community`. Add explicit assertions that the removed names do not appear.

- [ ] **Step 6: Run the developer toolkit tests**

Run: `python -m pytest developer/tests -v`

Expected: PASS.

- [ ] **Step 7: Commit task wiring**

```bash
git add developer/toolkit.py developer/toolkit.yaml developer/tests/test_toolkit_contract.py
git commit -m "feat: install community action server"
```

### Task 3: Public Documentation and End-to-End Verification

**Files:**
- Modify: `README.md`
- Modify: `docs/skills/repository-operations.md`
- Modify: `.github/workflows/dev_toolkit.yml` if the static search finds `BuildCommunity`
- Test: `developer/tests/test_toolkit_contract.py`

**Interfaces:**
- Consumes: RCC task `InstallCommunity`
- Produces: documented source-install command and durable recovery behavior

- [ ] **Step 1: Update all public references**

Run `rg -n 'BuildCommunity|build-community' . -g '!docs/superpowers/**'` and replace every active task/command reference with `InstallCommunity` or `install-community`. Update README text from “binary is at” to state that the built binary is installed at the current PATH-selected `action-server` target.

- [ ] **Step 2: Update canonical operational guidance**

Document target selection, PATH fallback requirements, atomic replacement, lack of privilege elevation, and both post-install smoke checks in `docs/skills/repository-operations.md`. Add the observed lifecycle diagnostic separately: deleted controlling PTY plus dead/zombie preload workers, sustained CPU, listening sockets, and HTTP timeouts indicate an orphaned broken process that must be terminated before reinstall/restart; do not claim that installation repairs it.

- [ ] **Step 3: Run static stale-name checks**

Run: `rg -n 'BuildCommunity|build-community' . -g '!docs/superpowers/**'`

Expected: no output.

- [ ] **Step 4: Run toolkit quality gates**

Run: `python -m ruff check developer`

Expected: PASS.

Run: `python -m pytest developer/tests -v`

Expected: PASS.

Run: `git diff --check`

Expected: PASS.

- [ ] **Step 5: Perform the real RCC installation acceptance**

Run: `rcc run -r developer/toolkit.yaml --dev -t InstallCommunity`

Expected: build and both source/installed smoke checks succeed.

Run: `command -v action-server && action-server version && action-server new --help`

Expected: the first command prints the replaced PATH target and both executable commands exit zero.

- [ ] **Step 6: Commit documentation and workflow changes**

```bash
git add README.md docs/skills/repository-operations.md .github/workflows developer/tests/test_toolkit_contract.py
git commit -m "docs: document community source installation"
```
