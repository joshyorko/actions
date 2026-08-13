import subprocess
import venv
import zipfile
from pathlib import Path

import tomllib


ROOT = Path(__file__).resolve().parents[2]
ACTIVE_CONTRACT_PATHS = (
    ROOT / "pyproject.toml",
    ROOT / "tests/action_server_tests/resources/no_conda/mcp/simple_mcp_server.py",
    ROOT.parent / ".github/workflows/_gen_workflows.py",
    ROOT.parent / ".github/workflows/actions_runtime_tests.yml",
    ROOT.parent / ".github/workflows/actions_runtime_pypi_release.yml",
    ROOT.parent / ".github/workflows/actions_runtime_binary_release.yml",
    ROOT.parent / ".github/workflows/actions_runtime_manylinux_release.yml",
    ROOT.parent / "actions/tests/actions_tests/test_lint_actions.py",
    ROOT / "src/actions/server/_common/oauth2_settings.py",
    ROOT / "src/actions/server/_oauth2.py",
    ROOT / "src/actions/server/_protocols.py",
    ROOT / "src/actions/server/_cli_impl.py",
)
# Deliberately excludes historical docs/changelogs, licenses, provenance,
# archived/inert fixtures, external URLs, and generic file:// URI handling.


def test_runtime_metadata_uses_published_active_dependencies():
    metadata = tomllib.loads((ROOT / "pyproject.toml").read_text())
    dependencies = metadata["tool"]["poetry"]["dependencies"]
    dev_dependencies = metadata["tool"]["poetry"]["group"]["dev"]["dependencies"]

    assert dependencies["actions-work-items"] == "^0.4.3"
    assert "sema4ai-data" not in dev_dependencies


def test_active_contract_paths_contain_no_legacy_runtime_contracts():
    forbidden = (
        "sema4ai-data",
        "from sema4ai",
        "import sema4ai",
        "sema4ai-config",
        "_SEMA4AI",
        "src/sema4ai",
        "_SEMA4AI",
    )

    violations = {
        str(path.relative_to(ROOT.parent)): token
        for path in ACTIVE_CONTRACT_PATHS
        for token in forbidden
        if token in path.read_text()
    }
    assert not violations, violations


def test_runtime_clean_wheels_interoperate_in_isolated_venv(tmp_path):
    packages = [ROOT.parent / name for name in ("actions", "actions-http-helper", "work-items", "action_server")]
    wheels = []
    for package in packages:
        output = tmp_path / package.name
        subprocess.run(
            ["poetry", "build", "-f", "wheel", "-o", str(output)],
            cwd=package,
            check=True,
            capture_output=True,
            text=True,
        )
        wheels.extend(output.glob("*.whl"))

    core_wheel = next(path for path in wheels if path.name.startswith("actions_core-"))
    work_items_wheel = next(path for path in wheels if path.name.startswith("actions_work_items-"))
    with zipfile.ZipFile(core_wheel) as archive:
        assert "actions/__init__.py" in archive.namelist()
    with zipfile.ZipFile(work_items_wheel) as archive:
        assert "actions/__init__.py" not in archive.namelist()

    runtime_wheel = next(path for path in wheels if path.name.startswith("actions_runtime-"))
    with zipfile.ZipFile(runtime_wheel) as archive:
        metadata = next(
            name for name in archive.namelist() if name.endswith("/METADATA")
        )
        assert "Requires-Dist: actions-work-items @ file:" not in archive.read(metadata).decode()

    env_dir = tmp_path / "venv"
    venv.create(env_dir, with_pip=True)
    python = env_dir / "bin/python"
    subprocess.run([str(python), "-m", "pip", "install", *map(str, wheels)], check=True)
    probe = (
        "import actions, actions.mcp, actions.work_items, actions.server, actions_http; "
        "assert actions and actions.mcp and actions.work_items and actions.server and actions_http"
    )
    subprocess.run([str(python), "-c", probe], check=True)
    subprocess.run([str(python), "-m", "actions.server", "--help"], check=True)
    subprocess.run([str(python), "-m", "actions.server.cli", "--help"], check=True)
