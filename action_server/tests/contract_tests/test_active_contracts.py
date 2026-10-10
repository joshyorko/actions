import ast
import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
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


def _private_core_imports(source: str) -> list[int]:
    violations = []
    tree = ast.parse(source)
    importlib_names: set[str] = set()
    import_module_names: set[str] = set()
    builtin_module_names: set[str] = set()
    builtin_import_names = {"__import__"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            importlib_names.update(
                alias.asname or alias.name
                for alias in node.names
                if alias.name == "importlib"
            )
            importlib_names.update(
                "importlib"
                for alias in node.names
                if alias.name.startswith("importlib.") and alias.asname is None
            )
            builtin_module_names.update(
                alias.asname or alias.name
                for alias in node.names
                if alias.name == "builtins"
            )
        elif isinstance(node, ast.ImportFrom) and node.module == "importlib":
            import_module_names.update(
                alias.asname or alias.name
                for alias in node.names
                if alias.name == "import_module"
            )
        elif isinstance(node, ast.ImportFrom) and node.module == "builtins":
            builtin_import_names.update(
                alias.asname or alias.name
                for alias in node.names
                if alias.name == "__import__"
            )

    def static_string(node):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            left, right = static_string(node.left), static_string(node.right)
            if left is not None and right is not None:
                return left + right
        return None

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if (node.module or "").startswith("actions._") or (
                node.module == "actions"
                and any(alias.name.startswith("_") for alias in node.names)
            ):
                violations.append(node.lineno)
        elif isinstance(node, ast.Import):
            if any(alias.name.startswith("actions._") for alias in node.names):
                violations.append(node.lineno)
        elif isinstance(node, ast.Call):
            function = node.func
            builtin_import = (
                isinstance(function, ast.Name) and function.id in builtin_import_names
            ) or (
                isinstance(function, ast.Attribute)
                and function.attr == "__import__"
                and isinstance(function.value, ast.Name)
                and function.value.id in builtin_module_names
            )
            module_import = (
                isinstance(function, ast.Name) and function.id in import_module_names
            ) or (
                isinstance(function, ast.Attribute)
                and function.attr == "import_module"
                and isinstance(function.value, ast.Name)
                and function.value.id in importlib_names
            )
            if not builtin_import and not module_import:
                continue
            keywords = {keyword.arg: keyword.value for keyword in node.keywords}
            module = static_string(node.args[0] if node.args else keywords.get("name"))
            if module is None:
                continue
            if module_import and module.startswith("."):
                package = static_string(
                    keywords.get(
                        "package", node.args[1] if len(node.args) > 1 else None
                    )
                )
                if package and (
                    package.startswith("actions._")
                    or (package == "actions" and module.startswith("._"))
                ):
                    violations.append(node.lineno)
            elif module.startswith("actions._"):
                violations.append(node.lineno)
            elif builtin_import and module == "actions":
                fromlist = keywords.get(
                    "fromlist", node.args[3] if len(node.args) > 3 else None
                )
                if isinstance(fromlist, (ast.List, ast.Tuple)) and any(
                    (static_string(value) or "").startswith("_")
                    for value in fromlist.elts
                ):
                    violations.append(node.lineno)
    return violations


def _private_core_imports_in_file(path: Path) -> list[int]:
    return _private_core_imports(path.read_text(encoding="utf-8"))


def _private_core_imports_in_tree(root: Path) -> list[str]:
    violations = []
    for path in sorted(root.rglob("*.py")):
        relative = path.relative_to(root).as_posix()
        violations.extend(
            f"{relative}:{line}" for line in _private_core_imports_in_file(path)
        )
    return violations


def _assert_runtime_wheel_python_members_match(
    wheel: Path, installed_members: dict[str, Path]
) -> list[tuple[str, Path, str]]:
    with zipfile.ZipFile(wheel) as archive:
        wheel_members = sorted(
            name for name in archive.namelist() if name.endswith(".py")
        )
        assert set(installed_members) == set(wheel_members), (
            "installed Runtime Python member inventory differs from selected wheel: "
            f"missing={sorted(set(wheel_members) - set(installed_members))}, "
            f"unexpected={sorted(set(installed_members) - set(wheel_members))}"
        )
        result = []
        for member in wheel_members:
            installed_path = installed_members[member].resolve()
            installed_bytes = installed_path.read_bytes()
            wheel_bytes = archive.read(member)
            installed_digest = hashlib.sha256(installed_bytes).hexdigest()
            wheel_digest = hashlib.sha256(wheel_bytes).hexdigest()
            assert installed_digest == wheel_digest, (
                f"installed Runtime member differs from selected wheel: {member} "
                f"installed={installed_digest} wheel={wheel_digest}"
            )
            result.append((member, installed_path, installed_digest))
    return result


def _assert_wheel_digest(
    wheel: Path, observed_digest: str, package_name: str
) -> None:
    expected_digest = hashlib.sha256(wheel.read_bytes()).hexdigest()
    assert observed_digest == expected_digest, (
        f"{package_name} wheel SHA-256 differs for {wheel}: "
        f"observed={observed_digest} expected={expected_digest}"
    )


def _assert_installed_runtime_wheel_has_no_private_core_imports(
    wheel: Path,
    installed_members: dict[str, Path],
    *,
    prefix: Path,
    checkout: Path,
) -> list[tuple[str, Path, str]]:
    environment_root = prefix.resolve()
    checkout_root = checkout.resolve()
    resolved_members = {}
    for member, path in installed_members.items():
        resolved = path.resolve()
        assert resolved.is_relative_to(environment_root), (
            f"installed Runtime module is outside the clean environment: {resolved}"
        )
        assert not resolved.is_relative_to(checkout_root), (
            f"installed Runtime module resolved into the checkout: {resolved}"
        )
        resolved_members[member] = resolved
    bound_members = _assert_runtime_wheel_python_members_match(
        wheel, resolved_members
    )
    violations = []
    for member, path, _ in bound_members:
        violations.extend(
            f"{member}:{line}" for line in _private_core_imports_in_file(path)
        )
    assert not violations, "Runtime imports Core-private modules:\n" + "\n".join(
        violations
    )
    return bound_members


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
        path.write_text(content, encoding="utf-8")
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
        path.write_text(content, encoding="utf-8")
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
    manifests = sorted((REPO / "templates").glob("*/package.yaml"))
    assert manifests

    for manifest in manifests:
        dependencies = {
            line.strip()[2:]
            for line in manifest.read_text().splitlines()
            if line.strip().startswith("- actions-")
        }
        assert "actions-core=1.0.2" in dependencies, str(manifest)
        assert not any(
            dependency.startswith("actions-core") and dependency != "actions-core=1.0.2"
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
    subprocess.run([str(python), "-m", "pip", "check"], check=True, env=environment)
    checkout = str(REPO.resolve())
    core_wheel = next(path for path in wheels if path.name.startswith("actions_core-"))
    runtime_wheel = next(
        path for path in wheels if path.name.startswith("actions_runtime-")
    )
    probe = f"""
import base64
import hashlib
import importlib
import importlib.metadata
import inspect
import json
import pathlib
import sys
import tempfile

environment_root = pathlib.Path(sys.prefix).resolve()
checkout_root = pathlib.Path({checkout!r}).resolve()
for name in ("actions", "actions.mcp", "actions.work_items", "actions.server", "actions_http"):
    module = importlib.import_module(name)
    origin = pathlib.Path(module.__file__).resolve()
    assert origin.is_relative_to(environment_root), origin
    assert not origin.is_relative_to(checkout_root), origin

from actions import ActionContext, ActionsListActionTypedDict, Request
from actions.server._protocols import JSONValue
assert ActionsListActionTypedDict.__required_keys__ == {{
    "name", "line", "file", "docs", "input_schema", "output_schema",
    "managed_params_schema", "options",
}}
assert JSONValue is not None
encoded_context = base64.b64encode(
    json.dumps({{"secrets": {{"token": "kept"}}}}).encode("utf-8")
).decode("ascii")
assert ActionContext(encoded_context).value == {{"secrets": {{"token": "kept"}}}}

from actions.server_integration import (
    DEFAULT_EXCLUSION_PATTERNS,
    EPManagedParameters,
    ManagedParameters,
    PluginManager,
    format_lint_results,
)
request = Request.model_validate({{"headers": {{"X-Request-ID": "request-1"}}, "cookies": {{}}}})
managed = ManagedParameters({{"request": request}})
plugin_manager = PluginManager()
plugin_manager.set_instance(EPManagedParameters, managed)
request_parameter = inspect.signature(lambda request: None).parameters["request"]
assert plugin_manager.get_instance(EPManagedParameters) is managed
assert managed.is_managed_param("request", param=request_parameter)
assert managed.inject_managed_params(
    inspect.signature(lambda request: None), None, {{}}, {{}}
) == {{"request": request}}
assert managed.get_request_contexts({{}}, {{}}).request is request
from actions.server._preload_actions.preload_actions_server_main import MessagesHandler
handler = MessagesHandler.__new__(MessagesHandler)
worker_plugins = handler._plugin_manager_kwargs(
    {{"request": {{"headers": {{"X-Request-ID": "worker-request"}}, "cookies": {{}}}}}}
)["plugin_manager"]
worker_request = worker_plugins.get_instance(EPManagedParameters).get_request_contexts({{}}, {{}}).request
assert worker_request.headers["X-Request-ID"] == "worker-request"

formatted = format_lint_results({{
    "file": "actions.py",
    "errors": [{{
        "range": {{"start": {{"line": 7}}}},
        "severity": 1,
        "message": "missing description",
    }}],
}})
assert formatted is not None and formatted.found_critical
assert "Error (line 7): missing description" in formatted.message

from actions.server.package.package_exclude import PackageExcludeHandler
with tempfile.TemporaryDirectory() as directory:
    root = pathlib.Path(directory)
    (root / ".git").mkdir()
    (root / ".git" / "config").write_text("ignored")
    (root / "keep.txt").write_text("kept")
    excludes = PackageExcludeHandler()
    excludes.fill_exclude_patterns(DEFAULT_EXCLUSION_PATTERNS)
    found = sorted(relative for _, relative in excludes.collect_files_excluding_patterns(root))
    assert found == ["keep.txt"], found

for name in (
    "actions.server._actions_process_pool",
    "actions.server._actions_import",
    "actions.server._encryption",
    "actions.server._new_project",
    "actions.server._preload_actions.preload_actions_server_main",
    "actions.server.package._package_metadata",
):
    importlib.import_module(name)

runtime_distribution = importlib.metadata.distribution("actions-runtime")
runtime_modules = []
for distribution_file in runtime_distribution.files or ():
    member = distribution_file.as_posix()
    if member.endswith(".py"):
        path = pathlib.Path(
            runtime_distribution.locate_file(distribution_file)
        ).resolve()
        runtime_modules.append({{
            "member": member,
            "path": str(path),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }})
assert runtime_modules, "installed Runtime distribution has no Python modules"
wheel_path = pathlib.Path({str(runtime_wheel.resolve())!r})
wheel_sha256 = hashlib.sha256(wheel_path.read_bytes()).hexdigest()
core_wheel_path = pathlib.Path({str(core_wheel.resolve())!r})
core_wheel_sha256 = hashlib.sha256(core_wheel_path.read_bytes()).hexdigest()
print("RUNTIME_WHEEL_MEMBER_INVENTORY=" + json.dumps({{
    "environment_prefix": str(pathlib.Path(sys.prefix).resolve()),
    "wheel_path": str(wheel_path),
    "wheel_sha256": wheel_sha256,
    "core_wheel_path": str(core_wheel_path),
    "core_wheel_sha256": core_wheel_sha256,
    "modules": runtime_modules,
}}, sort_keys=True))
"""
    probe_result = subprocess.run(
        [str(python), "-c", probe],
        check=True,
        capture_output=True,
        text=True,
        env=environment,
    )
    inventory_prefix = "RUNTIME_WHEEL_MEMBER_INVENTORY="
    inventory_lines = [
        line
        for line in probe_result.stdout.splitlines()
        if line.startswith(inventory_prefix)
    ]
    assert len(inventory_lines) == 1, (
        "clean Runtime probe did not emit exactly one wheel inventory; "
        f"stdout={probe_result.stdout!r} stderr={probe_result.stderr!r}"
    )
    inventory = json.loads(inventory_lines[0][len(inventory_prefix) :])
    assert inventory["wheel_path"] == str(runtime_wheel.resolve()), (
        f"Runtime probe selected a different wheel: {inventory['wheel_path']}"
    )
    assert inventory["core_wheel_path"] == str(core_wheel.resolve()), (
        f"Runtime probe selected a different Core wheel: {inventory['core_wheel_path']}"
    )
    _assert_wheel_digest(runtime_wheel, inventory["wheel_sha256"], "Runtime")
    _assert_wheel_digest(core_wheel, inventory["core_wheel_sha256"], "Core")
    environment_prefix = Path(inventory["environment_prefix"]).resolve()
    installed_members = {
        item["member"]: Path(item["path"]) for item in inventory["modules"]
    }
    assert len(installed_members) == len(inventory["modules"]), (
        "installed Runtime distribution contains duplicate Python member paths"
    )
    bound_members = _assert_installed_runtime_wheel_has_no_private_core_imports(
        runtime_wheel,
        installed_members,
        prefix=environment_prefix,
        checkout=REPO,
    )
    assert len(bound_members) == len(inventory["modules"])
    for member, path, digest in bound_members:
        observed = next(
            item for item in inventory["modules"] if item["member"] == member
        )
        assert observed["path"] == str(path)
        assert observed["sha256"] == digest
    print(
        "RUNTIME_WHEEL_PRIVATE_IMPORT_SCAN="
        + json.dumps(
            {
                "environment_prefix": str(environment_prefix),
                "runtime_wheel_path": str(runtime_wheel.resolve()),
                "runtime_wheel_sha256": inventory["wheel_sha256"],
                "core_wheel_path": str(core_wheel.resolve()),
                "core_wheel_sha256": inventory["core_wheel_sha256"],
                "members": [
                    {"path": member, "installed_path": str(path), "sha256": digest}
                    for member, path, digest in bound_members
                ],
            },
            sort_keys=True,
        ),
        flush=True,
    )
    subprocess.run(
        [str(python), "-m", "actions.server", "--help"], check=True, env=environment
    )
    subprocess.run(
        [
            str(
                python.parent
                / ("action-server.exe" if os.name == "nt" else "action-server")
            ),
            "--help",
        ],
        check=True,
        env=environment,
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
