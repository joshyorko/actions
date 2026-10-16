import importlib.util
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import tomllib
import zipfile
from pathlib import Path

import pytest

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
    "actions.link",
    "src/sema4ai",
)

REMOVED_PRODUCT_PATHS = (
    REPO / "templates/data-access-query",
    REPO / "templates/data-access-native",
    REPO / "templates/data-access-kb",
    REPO / "action_server/build-binary/tier_selector.py",
    REPO / "action_server/build-binary/vendor-frontend.py",
    REPO / ".github/workflows/vendor-integrity-check.yml",
    REPO / "action_server/tests/action_server_tests/test_data_package.py",
    REPO / "action_server/tests/action_server_tests/resources/data_package",
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
        {
            str(path.relative_to(REPO)): path.read_text(errors="replace")
            for path in _active_surface_files()
        }
    )


_VERIFIER_SPEC = importlib.util.spec_from_file_location(
    "runtime_wheel_verifier", ROOT / "scripts/verify_published_runtime_floor.py"
)
assert _VERIFIER_SPEC and _VERIFIER_SPEC.loader
_WHEEL_VERIFIER = importlib.util.module_from_spec(_VERIFIER_SPEC)
_VERIFIER_SPEC.loader.exec_module(_WHEEL_VERIFIER)
_private_core_imports = _WHEEL_VERIFIER._private_core_imports
_private_core_imports_in_file = _WHEEL_VERIFIER._private_core_imports_in_file
_private_core_imports_in_tree = _WHEEL_VERIFIER._private_core_imports_in_tree
_assert_runtime_wheel_python_members_match = (
    _WHEEL_VERIFIER._assert_runtime_wheel_python_members_match
)
_assert_wheel_digest = _WHEEL_VERIFIER._assert_wheel_digest
_assert_installed_runtime_wheel_has_no_private_core_imports = (
    _WHEEL_VERIFIER._assert_installed_runtime_wheel_has_no_private_core_imports
)


def test_installed_runtime_tree_scan_catches_unimported_private_core_modules(
    tmp_path: Path,
):
    installed_runtime = tmp_path / "site-packages"
    (installed_runtime / "actions/server").mkdir(parents=True)
    (installed_runtime / "actions/server/public.py").write_text(
        "from actions import ActionContext\n", encoding="utf-8"
    )
    (installed_runtime / "actions/server/unimported_direct.py").write_text(
        "from actions._protocols import JSONValue\n", encoding="utf-8"
    )
    (installed_runtime / "actions/server/unimported_alias.py").write_text(
        "import actions._action_context as context\n", encoding="utf-8"
    )
    (installed_runtime / "actions/server/unimported_dynamic.py").write_text(
        "import importlib as loader\n"
        "loader.import_module('actions.' + '_request')\n",
        encoding="utf-8",
    )
    (installed_runtime / "actions/server/_protocols.py").write_text(
        "JSONValue = object\n", encoding="utf-8"
    )

    assert _private_core_imports_in_tree(installed_runtime) == [
        "actions/server/unimported_alias.py:1",
        "actions/server/unimported_direct.py:1",
        "actions/server/unimported_dynamic.py:2",
    ]


def _write_wheel_fixture_member(path: Path, content: str) -> None:
    """Write the exact UTF-8 payload placed in a synthetic wheel member."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content.encode("utf-8"))


def test_wheel_fixture_member_writer_preserves_lf_bytes_on_windows(tmp_path: Path):
    member = "actions/server/_protocols.py"
    content = "JSONValue = object\n"
    wheel_bytes = content.encode("utf-8")
    windows_text_mode_bytes = content.replace("\n", "\r\n").encode("utf-8")
    assert wheel_bytes != windows_text_mode_bytes

    wheel = tmp_path / "actions_runtime-1.0.0-py3-none-any.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr(member, wheel_bytes)
    installed = tmp_path / "site-packages" / member
    _write_wheel_fixture_member(installed, content)

    with zipfile.ZipFile(wheel) as archive:
        assert installed.read_bytes() == archive.read(member) == wheel_bytes


def test_runtime_wheel_member_binding_rejects_installed_byte_mismatch(tmp_path: Path):
    wheel = tmp_path / "actions_runtime-1.0.0-py3-none-any.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr("actions/server/kept.py", "value = 1\n")
        archive.writestr("actions/server/extra.py", "value = 2\n")
    installed = tmp_path / "site-packages/actions/server"
    installed.mkdir(parents=True)
    (installed / "kept.py").write_text("value = 1\n", encoding="utf-8")
    (installed / "extra.py").write_text("value = 3\n", encoding="utf-8")

    with pytest.raises(AssertionError, match="installed Runtime member differs"):
        _assert_runtime_wheel_python_members_match(
            wheel,
            {
                "actions/server/kept.py": installed / "kept.py",
                "actions/server/extra.py": installed / "extra.py",
            },
        )


def test_runtime_wheel_member_binding_rejects_incomplete_inventory(tmp_path: Path):
    wheel = tmp_path / "actions_runtime-1.0.0-py3-none-any.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr("actions/server/one.py", "value = 1\n")
        archive.writestr("actions/server/two.py", "value = 2\n")
    installed = tmp_path / "site-packages/actions/server/one.py"
    installed.parent.mkdir(parents=True)
    installed.write_text("value = 1\n", encoding="utf-8")

    with pytest.raises(AssertionError, match="member inventory differs"):
        _assert_runtime_wheel_python_members_match(
            wheel, {"actions/server/one.py": installed}
        )


def test_runtime_wheel_digest_binding_reports_selected_artifact_mismatch(
    tmp_path: Path,
):
    wheel = tmp_path / "actions_runtime-1.0.0-py3-none-any.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr("actions/server/module.py", "value = 1\n")

    with pytest.raises(AssertionError, match="Runtime wheel SHA-256 differs"):
        _assert_wheel_digest(wheel, "0" * 64, "Runtime")


def test_installed_runtime_wheel_scan_rejects_unimported_private_core_import(
    tmp_path: Path,
):
    wheel = tmp_path / "actions_runtime-1.0.0-py3-none-any.whl"
    members = {
        "actions/server/public.py": "from actions import ActionContext\n",
        "actions/server/unimported.py": "from actions._protocols import JSONValue\n",
        "actions/server/_protocols.py": "JSONValue = object\n",
    }
    with zipfile.ZipFile(wheel, "w") as archive:
        for name, content in members.items():
            archive.writestr(name, content)
    environment = tmp_path / "venv"
    site_packages = environment / "lib/python3.12/site-packages"
    installed_members = {}
    for name, content in members.items():
        path = site_packages / name
        path.parent.mkdir(parents=True, exist_ok=True)
        _write_wheel_fixture_member(path, content)
        installed_members[name] = path

    with pytest.raises(
        AssertionError,
        match=r"Runtime imports Core-private modules:\n.*unimported.py:1",
    ):
        _assert_installed_runtime_wheel_has_no_private_core_imports(
            wheel,
            installed_members,
            prefix=environment,
            checkout=tmp_path / "checkout",
        )


def test_installed_runtime_wheel_scan_allows_public_core_and_runtime_json_modules(
    tmp_path: Path,
):
    wheel = tmp_path / "actions_runtime-1.0.0-py3-none-any.whl"
    members = {
        "actions/server/public_api.py": "from actions import ActionContext\n",
        "actions/server/_protocols.py": "JSONValue = object\n",
    }
    with zipfile.ZipFile(wheel, "w") as archive:
        for name, content in members.items():
            archive.writestr(name, content)
    environment = tmp_path / "venv"
    site_packages = environment / "lib/python3.12/site-packages"
    installed_members = {}
    for name, content in members.items():
        path = site_packages / name
        path.parent.mkdir(parents=True, exist_ok=True)
        _write_wheel_fixture_member(path, content)
        installed_members[name] = path

    result = _assert_installed_runtime_wheel_has_no_private_core_imports(
        wheel,
        installed_members,
        prefix=environment,
        checkout=tmp_path / "checkout",
    )

    assert [member for member, _, _ in result] == sorted(members)


@pytest.mark.parametrize(
    "source",
    [
        "from actions import _request as request",
        "import importlib as loader\nloader.import_module('actions._request')",
        "from importlib import import_module as load\nload('actions._request')",
        "__import__('actions._request')",
        "import importlib\nimportlib.import_module('._request', package='actions')",
        "__import__('actions', fromlist=['_request'])",
        "import importlib\nimportlib.import_module('actions.' + '_request')",
        "import importlib\nimportlib.import_module(name='actions._request')",
        "__import__(name='actions._request')",
        "import importlib\nimportlib.import_module('.child', package='actions._request')",
        "import importlib.util\nimportlib.import_module('actions._request')",
        "from builtins import __import__ as load\nload('actions._request')",
        "import builtins as loader\nloader.__import__('actions._request')",
    ],
)
def test_private_import_detection_covers_aliases_and_static_dynamic_imports(source):
    assert _private_core_imports(source)


@pytest.mark.parametrize(
    "source",
    [
        "from actions import ActionContext as Context",
        "from actions.server_integration import PluginManager",
        "import importlib\nimportlib.import_module('actions.server')",
        "import importlib\nimportlib.import_module('other._request')",
        "import importlib\nimportlib.import_module(module_name)",
        "import actions.server._models",
    ],
)
def test_private_import_detection_preserves_public_and_runtime_modules(source):
    assert not _private_core_imports(source)


def test_runtime_imports_core_only_through_public_modules():
    source_root = REPO / "action_server/src/actions/server"
    violations = []
    for path in sorted(source_root.rglob("*.py")):
        violations.extend(
            f"{path.relative_to(REPO)}:{line}"
            for line in _private_core_imports_in_file(path)
        )

    assert not violations, "Runtime imports Core-private modules:\n" + "\n".join(
        violations
    )


def test_runtime_import_scan_decodes_utf8_source(tmp_path: Path):
    source = tmp_path / "unicode.py"
    source.write_bytes("# \u038f\n".encode("utf-8"))

    assert _private_core_imports_in_file(source) == []


def test_template_package_script_is_executable_for_direct_workflow_invocation():
    script = REPO / "templates/packaging/create-templates-package.sh"
    relative_script = script.relative_to(REPO).as_posix()
    tracked_mode = subprocess.run(
        ["git", "ls-files", "--stage", "--", relative_script],
        cwd=REPO,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.split(maxsplit=1)[0]
    assert tracked_mode == "100755", str(script)
    if os.name != "nt":
        assert script.stat().st_mode & stat.S_IXUSR, str(script)

    for workflow_name, config_name in (
        ("deploy-beta-templates.yml", "templates-beta.json"),
        ("deploy-templates.yml", "templates-prod.json"),
    ):
        workflow = (REPO / ".github/workflows" / workflow_name).read_text()
        assert f"./create-templates-package.sh {config_name}" in workflow


def test_removed_product_paths_do_not_exist():
    remaining_paths = [
        str(path.relative_to(REPO)) for path in REMOVED_PRODUCT_PATHS if path.exists()
    ]
    assert not remaining_paths


def test_runtime_has_no_data_server_or_data_context_compatibility():
    sources = {
        "tools": (
            REPO / "action_server/src/actions/server/_common/tools.py"
        ).read_text(),
        "contexts": (REPO / "actions/src/actions/_action_context.py").read_text(),
        "managed_parameters": (
            REPO / "actions/src/actions/_managed_parameters.py"
        ).read_text(),
        "run": (REPO / "action_server/src/actions/server/_actions_run.py").read_text(),
        "import": (
            REPO / "action_server/src/actions/server/_actions_import.py"
        ).read_text(),
        "package_metadata": (
            REPO / "action_server/src/actions/server/package/_package_metadata.py"
        ).read_text(),
    }
    violations = {
        f"{name}:{token}"
        for name, text in sources.items()
        for token in (
            "DataServerTool",
            "DataContext",
            "x-data-context",
            "data_package_metadata",
        )
        if token in text
    }
    assert not violations, sorted(violations)


def test_project_templates_use_embedded_assets_without_hosted_update_transport():
    helpers = (
        REPO / "action_server/src/actions/server/_new_project_helpers.py"
    ).read_text()
    assert "downloads.robocorp.com" not in helpers
    assert "TEMPLATES_METADATA_URL" not in helpers
    assert "TEMPLATES_PACKAGE_URL" not in helpers
    assert "actions_http.get" not in helpers


def test_active_guidance_and_ci_have_no_private_product_lane():
    roots = (
        REPO / "docs/BUILD_INSTRUCTIONS.md",
        REPO / "docs/COMMUNITY_UI_SPEC.md",
        REPO / ".github/copilot-instructions.md",
        REPO / ".github/workflows/copilot-setup-steps.yml",
        REPO / ".github/workflows/frontend-build-unauthenticated.yml",
    )
    violations = {
        f"{path.relative_to(REPO)}:{token}"
        for path in roots
        if path.exists()
        for token in (
            "NPM_TOKEN",
            "npm.pkg.github.com",
            "--tier=enterprise",
            "source=vendored",
            "source=registry",
        )
        if token in path.read_text()
    }
    sorted_violations = sorted(violations)
    assert not sorted_violations


def test_runtime_metadata_uses_published_active_dependencies():
    metadata = tomllib.loads((ROOT / "pyproject.toml").read_text())
    dependencies = metadata["tool"]["poetry"]["dependencies"]
    assert dependencies["actions-work-items"] == "^0.4.4"


def test_template_manifests_pin_supported_worker_core():
    expected_core_versions = {
        "advanced": "1.0.2",
        "basic": "1.0.2",
        "canvas-query": "1.0.3",
        "minimal": "1.0.2",
        "mcp-v2-showcase": "1.0.2",
        "workflow-producer-consumer": "1.0.2",
    }
    manifests = {
        manifest.parent.name: manifest
        for manifest in sorted((REPO / "templates").glob("*/package.yaml"))
    }
    assert set(manifests) == set(expected_core_versions)

    for template_name, manifest in manifests.items():
        dependencies = {
            line.strip()[2:]
            for line in manifest.read_text().splitlines()
            if line.strip().startswith("- actions-")
        }
        expected_core = f"actions-core={expected_core_versions[template_name]}"
        assert expected_core in dependencies, str(manifest)
        assert not any(
            dependency.startswith("actions-core") and dependency != expected_core
            for dependency in dependencies
        ), str(manifest)

        expected_work_items = (
            {"actions-work-items=0.4.4"}
            if manifest.parent.name == "workflow-producer-consumer"
            else set()
        )
        assert {
            dependency
            for dependency in dependencies
            if dependency.startswith("actions-work-items")
        } == expected_work_items, str(manifest)


def test_template_sources_use_actions_core_without_module_name_collision():
    template_roots = sorted(
        path.parent for path in (REPO / "templates").glob("*/package.yaml")
    )
    assert template_roots

    violations = []
    for template_root in template_roots:
        for source in sorted(template_root.rglob("*.py")):
            text = source.read_text()
            if "sema4ai.actions" in text or "robocorp.actions" in text:
                violations.append(str(source.relative_to(REPO)))
        if (template_root / "actions.py").exists():
            violations.append(str((template_root / "actions.py").relative_to(REPO)))

    assert not violations, ", ".join(violations)


def _build_wheels(output: Path, python: Path) -> list[Path]:
    for name in ("actions", "actions-http-helper", "work-items", "action_server"):
        package = REPO / name
        command = [
            "poetry",
            "build",
            "-f",
            "wheel",
            "-o",
            str(output),
        ]
        environment = os.environ.copy()
        environment.pop("VIRTUAL_ENV", None)
        environment.pop("POETRY_ACTIVE", None)
        environment.pop("PYTHONPATH", None)
        if name == "action_server":
            environment["ACTION_SERVER_SKIP_DOWNLOAD_IN_BUILD"] = "true"
            subprocess.run(
                [str(python), "scripts/build_oauth2_config.py"],
                cwd=package,
                check=True,
                env=environment,
            )
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
    candidate: Path | None
    if configured:
        candidate = Path(configured)
    elif sys.version_info[:2] in {(3, 12), (3, 13)}:
        # Keep clean installs and probes on the active package interpreter
        # instead of choosing a newer supported interpreter from PATH.
        candidate = Path(sys.executable)
    else:
        candidate = next(
            (
                Path(found)
                for version in ("3.13", "3.12")
                if (found := shutil.which(f"python{version}"))
            ),
            None,
        )
    if candidate is None or not candidate.exists():
        pytest.skip("Runtime wheel contract requires supported Python 3.13 or 3.12")
    return candidate


def test_runtime_python_prefers_the_active_supported_interpreter(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    active_python = tmp_path / "python3.12"
    path_python = tmp_path / "python3.13"
    active_python.touch()
    path_python.touch()
    monkeypatch.delenv("ACTIONS_RUNTIME_TEST_PYTHON", raising=False)
    monkeypatch.setattr(sys, "executable", str(active_python))
    monkeypatch.setattr(sys, "version_info", (3, 12, 0, "final", 0))
    monkeypatch.setattr(
        shutil,
        "which",
        lambda name: str(path_python) if name == "python3.13" else None,
    )

    assert _runtime_python() == active_python


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
    core_wheel = next(path for path in wheels if path.name.startswith("actions_core-"))
    runtime_wheel = next(
        path for path in wheels if path.name.startswith("actions_runtime-")
    )
    _WHEEL_VERIFIER.verify_oauth_input_binding(runtime_wheel, ROOT)
    with tempfile.TemporaryDirectory(prefix="runtime-wheel-probe-") as directory:
        _WHEEL_VERIFIER.verify_installed_runtime_wheel(
            python, runtime_wheel, Path(directory), REPO, core_wheel=core_wheel
        )


def test_runtime_clean_wheels_install_outside_checkout_in_both_uninstall_orders(
    tmp_path,
):
    runtime_python = _runtime_python()
    wheelhouse = tmp_path / "wheelhouse"
    wheelhouse.mkdir()
    wheels = _build_wheels(wheelhouse, runtime_python)

    core_wheel = next(path for path in wheels if path.name.startswith("actions_core-"))
    work_items_wheel = next(
        path for path in wheels if path.name.startswith("actions_work_items-")
    )
    with zipfile.ZipFile(core_wheel) as archive:
        assert "actions/__init__.py" in archive.namelist()
    with zipfile.ZipFile(work_items_wheel) as archive:
        assert "actions/__init__.py" not in archive.namelist()

    runtime_wheel = next(
        path for path in wheels if path.name.startswith("actions_runtime-")
    )
    runtime_files = _wheel_files(runtime_wheel)
    metadata_name = next(name for name in runtime_files if name.endswith("/METADATA"))
    assert (
        "Requires-Dist: actions-core (>=1.0.2,<2.0.0)" in runtime_files[metadata_name]
    )
    assert (
        "Requires-Dist: actions-http-helper (>=1.0.3,<2.0.0)"
        in runtime_files[metadata_name]
    )
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

    for order in (
        ("actions-runtime", "actions-core"),
        ("actions-core", "actions-runtime"),
    ):
        env_dir = tmp_path / ("venv-" + "-".join(order))
        subprocess.run([str(runtime_python), "-m", "venv", str(env_dir)], check=True)
        python = env_dir / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        _install_and_probe(python, wheels)
        environment = os.environ.copy()
        environment.pop("PYTHONPATH", None)
        subprocess.run(
            [str(python), "-m", "pip", "uninstall", "-y", *order],
            check=True,
            env=environment,
        )
