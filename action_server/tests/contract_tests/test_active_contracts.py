import json
import os
import shutil
import subprocess
import venv
import zipfile
from pathlib import Path

import pytest
import tomllib


ROOT = Path(__file__).resolve().parents[2]
REPO = ROOT.parent
HISTORICAL_DOCS = {
    REPO / "action_server/docs/guides/13-post-run-script.md",
    REPO / "action_server/docs/guides/18-data-packages.md",
    REPO / "action_server/docs/guides/20-chat-files.md",
}
EXCLUDED_NAMES = {".git", ".serena", ".hermes", "__pycache__", "node_modules", "dist"}
EXCLUDED_FILES = {"CHANGELOG.md", "LICENSE", "NOTICE.md", "manifest.json"}
FORBIDDEN_ACTIVE_CONTRACTS = (
    "sema4ai-data",
    "sema4ai-devutils",
    "sema4ai-http-helper",
    "sema4ai-action-server",
    "sema4ai-actions",
    "sema4ai-mcp",
    "from sema4ai",
    "import sema4ai",
    "@sema4ai/",
    "SEMA4AI_HOME",
    "SEMA4AI_BUILD_TIER",
    "sema4ai_config",
    "get_sema4ai",
    "set_sema4ai",
    "mode: sema4ai",
    "/sema4ai/oauth2",
    "sema4ai.link",
    "src/sema4ai",
)


def _files_under(root: Path) -> list[Path]:
    if root.is_file():
        return [root]
    return sorted(
        path
        for path in root.rglob("*")
        if path.is_file()
        and path.name not in EXCLUDED_FILES
        and not any(part in EXCLUDED_NAMES for part in path.relative_to(root).parts)
        and path not in HISTORICAL_DOCS
    )


def _active_surface_files() -> list[Path]:
    template_metadata = [
        REPO / "templates/packaging/templates-prod.json",
        REPO / "templates/packaging/templates-beta.json",
    ]
    supported_ids = {
        template["id"]
        for metadata_path in template_metadata
        for template in json.loads(metadata_path.read_text())["templates"]
    }
    roots = [
        REPO / "README.md",
        REPO / "actions/README.md",
        REPO / "actions/docs/api",
        REPO / "mcp/docs/api",
        REPO / "action_server/README.md",
        REPO / "action_server/docs/guides",
        REPO / "action_server/frontend/package.json",
        REPO / "action_server/frontend/package-lock.json",
        REPO / "action_server/frontend/vite.config.js",
        REPO / "action_server/frontend/feature-boundaries.json",
        REPO / "action_server/frontend/src",
        REPO / "action_server/src/actions/server",
        *template_metadata,
        *(REPO / "templates" / template_id for template_id in supported_ids),
    ]
    return sorted({path for root in roots for path in _files_under(root)})


def _assert_no_legacy_contracts(texts: dict[str, str]) -> None:
    violations = {
        f"{name}:{token}"
        for name, text in texts.items()
        for token in FORBIDDEN_ACTIVE_CONTRACTS
        if token in text
    }
    assert not violations, sorted(violations)


def test_active_contracts_scan_supported_docs_templates_and_build_inputs():
    _assert_no_legacy_contracts(
        {str(path.relative_to(REPO)): path.read_text(errors="replace") for path in _active_surface_files()}
    )


def test_runtime_metadata_uses_published_active_dependencies():
    metadata = tomllib.loads((ROOT / "pyproject.toml").read_text())
    dependencies = metadata["tool"]["poetry"]["dependencies"]
    assert dependencies["actions-work-items"] == "^0.4.3"


def _build_wheels(output: Path, python: Path) -> list[Path]:
    for name in ("actions", "actions-http-helper", "work-items", "action_server"):
        package = REPO / name
        command = [
            "uv",
            "run",
            "--no-project",
            "--python",
            str(python),
            "--with",
            "poetry",
            "poetry",
            "build",
            "-f",
            "wheel",
            "-o",
            str(output),
        ]
        environment = os.environ.copy()
        if name == "action_server":
            environment["ACTION_SERVER_SKIP_DOWNLOAD_IN_BUILD"] = "true"
        subprocess.run(
            command,
            cwd=package,
            check=True,
            capture_output=True,
            text=True,
            env=environment,
        )
    return sorted(output.glob("*.whl"))


def _wheel_files(wheel: Path) -> dict[str, str]:
    with zipfile.ZipFile(wheel) as archive:
        return {
            name: archive.read(name).decode(errors="replace")
            for name in archive.namelist()
            if not name.endswith(".pyc")
        }


def _runtime_python() -> Path:
    configured = os.environ.get("ACTIONS_RUNTIME_TEST_PYTHON")
    if configured:
        candidate = Path(configured)
    else:
        candidate = next(
            (Path(found) for version in ("3.13", "3.12") if (found := shutil.which(f"python{version}"))),
            None,
        )
    if candidate is None or not candidate.exists():
        pytest.skip("Runtime wheel contract requires supported Python 3.13 or 3.12")
    return candidate


def _install_and_probe(python: Path, wheels: list[Path]) -> None:
    wheelhouse = wheels[0].parent
    environment = os.environ.copy()
    environment.pop("PYTHONPATH", None)
    subprocess.run(
        [
            str(python),
            "-m",
            "pip",
            "install",
            "--find-links",
            str(wheelhouse),
            *map(str, wheels),
        ],
        check=True,
        env=environment,
    )
    checkout = str(REPO.resolve())
    probe = f"""
import importlib
import pathlib

for name in ("actions", "actions.mcp", "actions.work_items", "actions.server", "actions_http"):
    module = importlib.import_module(name)
    origin = pathlib.Path(module.__file__).resolve()
    assert not str(origin).startswith({checkout!r}), origin
"""
    subprocess.run([str(python), "-c", probe], check=True, env=environment)
    subprocess.run(
        [str(python), "-m", "actions.server", "--help"], check=True, env=environment
    )
    subprocess.run(
        [str(python.parent / "action-server"), "--help"], check=True, env=environment
    )


def test_runtime_clean_wheels_install_outside_checkout_in_both_uninstall_orders(tmp_path):
    runtime_python = _runtime_python()
    wheelhouse = tmp_path / "wheelhouse"
    wheelhouse.mkdir()
    wheels = _build_wheels(wheelhouse, runtime_python)

    core_wheel = next(path for path in wheels if path.name.startswith("actions_core-"))
    work_items_wheel = next(path for path in wheels if path.name.startswith("actions_work_items-"))
    with zipfile.ZipFile(core_wheel) as archive:
        assert "actions/__init__.py" in archive.namelist()
    with zipfile.ZipFile(work_items_wheel) as archive:
        assert "actions/__init__.py" not in archive.namelist()

    runtime_wheel = next(path for path in wheels if path.name.startswith("actions_runtime-"))
    runtime_files = _wheel_files(runtime_wheel)
    metadata_name = next(name for name in runtime_files if name.endswith("/METADATA"))
    record_name = next(name for name in runtime_files if name.endswith("/RECORD"))
    required_payload = {
        "actions/server/_settings.py",
        "actions/server/_oauth2.py",
        "actions/server/_common/oauth2_settings.py",
        "actions/server/_common/url_callback_server.py",
        "actions/server/vendored_deps/oauth2_settings.py",
        "actions/server/vendored_deps/url_callback_server.py",
    }
    assert required_payload <= runtime_files.keys()
    assert " @ file:" not in runtime_files[metadata_name]
    assert "direct_url.json" not in runtime_files[record_name]
    _assert_no_legacy_contracts(
        {
            name: runtime_files[name]
            for name in (metadata_name, record_name, *required_payload)
        }
    )

    for order in (("actions-runtime", "actions-core"), ("actions-core", "actions-runtime")):
        env_dir = tmp_path / ("venv-" + "-".join(order))
        subprocess.run([str(runtime_python), "-m", "venv", str(env_dir)], check=True)
        python = env_dir / "bin/python"
        _install_and_probe(python, wheels)
        environment = os.environ.copy()
        environment.pop("PYTHONPATH", None)
        subprocess.run(
            [str(python), "-m", "pip", "uninstall", "-y", *order],
            check=True,
            env=environment,
        )
