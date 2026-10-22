"""Verify a selected installed Runtime wheel and its public dependency floor."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import zipfile
from email.parser import BytesParser
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import url2pathname

EXPECTED_CORE = "1.0.2"
EXPECTED_HELPER = "1.0.3"
EXPECTED_RUNTIME = "1.0.4"
EXPECTED_PUBLIC_PACKAGES = {
    "actions-core": {
        "version": EXPECTED_CORE,
        "url": "https://files.pythonhosted.org/packages/b6/ed/33c5999ac5e932434fcc5b392420efdf9b25922ca02a76622b856759ea16/actions_core-1.0.2-py3-none-any.whl",
        "sha256": "9d527edf540978172178894546add75f117f240786aec804cb75c308615a7e80",
    },
    "actions-http-helper": {
        "version": EXPECTED_HELPER,
        "url": "https://files.pythonhosted.org/packages/53/3b/cefc0608e6ec71697c60c68ede2efa306fd7d50b1736c4b6b094b3424dc6/actions_http_helper-1.0.3-py3-none-any.whl",
        "sha256": "46ed7ce0e0d3e2e05456d937b5b24bc9dfa0d7d4b98f8119b9fdf00d4fa7e9f9",
    },
}
REPO_ROOT = Path(__file__).resolve().parents[2]
OAUTH_INPUTS = {
    "actions_config": "actions-oauth-config.yaml",
    "default_user_config": "oauth-config.yaml",
}


def verify_oauth_input_binding(wheel: Path, project: Path) -> dict[str, str]:
    """Read generated literals without executing them and bind owned raw inputs."""
    try:
        with zipfile.ZipFile(wheel) as archive:
            source = archive.read("actions/server/_oauth2_config.py").decode("utf-8")
        values = {}
        for node in ast.parse(source).body:
            if (
                not isinstance(node, ast.Assign)
                or len(node.targets) != 1
                or not isinstance(node.targets[0], ast.Name)
                or node.targets[0].id not in {"FILE_CONTENTS", "INPUT_SHA256"}
                or node.targets[0].id in values
            ):
                raise ValueError("unexpected generated statement")
            values[node.targets[0].id] = ast.literal_eval(node.value)
    except (KeyError, UnicodeError, SyntaxError, ValueError) as error:
        raise RuntimeError(
            "OAuth2 generated module must contain two literal mappings"
        ) from error
    contents = {
        key: (project / "oauth2" / filename).read_bytes().decode("utf-8")
        for key, filename in OAUTH_INPUTS.items()
    }
    hashes = {
        filename: hashlib.sha256(contents[key].encode("utf-8")).hexdigest()
        for key, filename in OAUTH_INPUTS.items()
    }
    if values != {"FILE_CONTENTS": contents, "INPUT_SHA256": hashes}:
        raise RuntimeError("OAuth2 generated values differ from owned input bytes")
    return hashes


def verify_selected_runtime_origin(wheel: Path, direct_url: dict) -> None:
    """Require pip's installed origin to name the exact selected local archive."""
    digest = hashlib.sha256(wheel.read_bytes()).hexdigest()
    origin = urlsplit(direct_url.get("url", ""))
    if (
        origin.scheme != "file"
        or origin.netloc
        or Path(url2pathname(origin.path)).resolve() != wheel.resolve()
        or direct_url.get("archive_info", {}).get("hashes", {}).get("sha256") != digest
    ):
        raise RuntimeError("Installed origin differs from the selected Runtime wheel")


def validate_runtime_metadata(
    wheel: Path, *, expected_runtime: str = EXPECTED_RUNTIME
) -> None:
    with zipfile.ZipFile(wheel) as archive:
        paths = [
            name for name in archive.namelist() if name.endswith(".dist-info/METADATA")
        ]
        if len(paths) != 1:
            raise ValueError(f"Expected one Runtime wheel METADATA: {wheel.name}")
        metadata = BytesParser().parsebytes(archive.read(paths[0]))
    if metadata.get("Name") != "actions-runtime":
        raise ValueError(f"Unexpected distribution in {wheel.name}")
    if metadata.get("Version") != expected_runtime:
        raise ValueError(f"Unexpected Runtime version in {wheel.name}")


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
    violations: list[str] = []
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


def _assert_wheel_digest(wheel: Path, observed_digest: str, package_name: str) -> None:
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
        assert resolved.is_relative_to(
            environment_root
        ), f"installed Runtime module is outside the clean environment: {resolved}"
        assert not resolved.is_relative_to(
            checkout_root
        ), f"installed Runtime module resolved into the checkout: {resolved}"
        resolved_members[member] = resolved
    bound_members = _assert_runtime_wheel_python_members_match(wheel, resolved_members)
    violations: list[str] = []
    for member, path, _ in bound_members:
        violations.extend(
            f"{member}:{line}" for line in _private_core_imports_in_file(path)
        )
    assert not violations, "Runtime imports Core-private modules:\n" + "\n".join(
        violations
    )
    return bound_members


def select_runtime_wheel(directory: Path) -> Path:
    candidates = []
    for wheel in sorted(directory.glob("actions_runtime-*.whl")):
        if "-cp312-" not in wheel.name:
            continue
        validate_runtime_metadata(wheel)
        candidates.append(wheel)
    if len(candidates) != 1:
        raise ValueError(
            f"Expected exactly one cp312 actions-runtime {EXPECTED_RUNTIME} wheel in "
            f"{directory}, found {len(candidates)}"
        )
    return candidates[0]


def isolated_environment(source: dict[str, str] | None = None) -> dict[str, str]:
    environment = dict(os.environ if source is None else source)
    for name in ("PYTHONPATH", "PYTHONHOME", "PYTHONUSERBASE", "PYTHONSTARTUP"):
        environment.pop(name, None)
    environment["PYTHONNOUSERSITE"] = "1"
    return environment


def source_checkout_root(project: Path) -> Path:
    """Cover monorepo siblings without expanding an isolated /project to /."""
    project = project.resolve()
    parent = project.parent
    if (
        project.name == "action_server"
        and (parent / "AGENTS.md").is_file()
        and (parent / "actions/src").is_dir()
        and (parent / "actions-http-helper/src").is_dir()
    ):
        return parent
    return project


def assert_no_checkout_imports(
    repository: Path,
    search_paths: list[str],
    module_files: dict[str, str],
) -> None:
    root = repository.resolve()
    offenders: list[str] = []
    entries = [
        (f"sys.path[{index}]", value) for index, value in enumerate(search_paths)
    ]
    entries.extend((f"module {name}", value) for name, value in module_files.items())
    for source, value in entries:
        if not value:
            value = "."
        path = Path(value).resolve()
        try:
            path.relative_to(root)
        except ValueError:
            continue
        offenders.append(f"{source}: {path}")
    if offenders:
        raise RuntimeError(
            "Imports or module search paths point into the source checkout:\n"
            + "\n".join(offenders)
        )


def build_import_path_guard(repository: Path) -> str:
    """Return a child-interpreter preflight that rejects checkout search paths."""
    return f"""
import pathlib, sys
root = pathlib.Path({str(repository.resolve())!r})
offenders = []
for index, value in enumerate(sys.path):
    path = pathlib.Path(value or pathlib.Path.cwd()).resolve()
    try:
        path.relative_to(root)
    except ValueError:
        continue
    offenders.append(f"sys.path[{{index}}]: {{path}}")
if offenders:
    message = "Python search paths point into the source checkout:\\n"
    raise SystemExit(message + "\\n".join(offenders))
"""


def verify_public_package_report(report_path: Path) -> dict[str, dict[str, str]]:
    report = json.loads(report_path.read_text(encoding="utf-8"))
    observed: dict[str, dict[str, str]] = {}
    for item in report.get("install", []):
        metadata = item.get("metadata", {})
        name = metadata.get("name", "").lower().replace("_", "-")
        if name not in EXPECTED_PUBLIC_PACKAGES:
            continue
        expected = EXPECTED_PUBLIC_PACKAGES[name]
        if metadata.get("version") != expected["version"]:
            raise RuntimeError(f"Unexpected {name} version in pip report")
        download = item.get("download_info", {})
        url = download.get("url", "")
        if url != expected["url"] or urlsplit(url).hostname != "files.pythonhosted.org":
            raise RuntimeError(f"Unexpected {name} public PyPI wheel URL")
        sha256 = download.get("archive_info", {}).get("hashes", {}).get("sha256")
        if sha256 != expected["sha256"]:
            raise RuntimeError(f"Unexpected {name} PyPI artifact SHA-256")
        observed[name] = {"version": expected["version"], "url": url, "sha256": sha256}
    if set(observed) != set(EXPECTED_PUBLIC_PACKAGES):
        missing = sorted(set(EXPECTED_PUBLIC_PACKAGES) - set(observed))
        raise RuntimeError(f"Pip report omits required public packages: {missing}")
    return observed


def install_command(python: Path, wheel: Path, report: Path) -> list[str]:
    return [
        str(python),
        "-m",
        "pip",
        "install",
        "--isolated",
        "--no-cache-dir",
        "--index-url",
        "https://pypi.org/simple",
        "--only-binary=:all:",
        "--report",
        str(report),
        str(wheel.resolve()),
        f"actions-core=={EXPECTED_CORE}",
        f"actions-http-helper=={EXPECTED_HELPER}",
    ]


def verify_installed_runtime_wheel(
    python: Path,
    runtime_wheel: Path,
    isolated_workdir: Path,
    checkout: Path,
    *,
    core_wheel: Path | None = None,
    expected_runtime: str = EXPECTED_RUNTIME,
) -> dict:
    """Bind every installed Runtime Python member to the selected wheel."""
    validate_runtime_metadata(runtime_wheel, expected_runtime=expected_runtime)
    environment = isolated_environment()
    checkout = checkout.resolve()
    probe = (
        build_import_path_guard(Path(checkout))
        + f"""
import base64
import hashlib
import importlib
import importlib.metadata
import inspect
import json
import pathlib
import sys
import tempfile

assert importlib.metadata.version("actions-runtime") == {expected_runtime!r}
environment_root = pathlib.Path(sys.prefix).resolve()
checkout_root = pathlib.Path({str(checkout)!r}).resolve()
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
core_wheel_path = {str(core_wheel.resolve()) if core_wheel else None!r}
core_wheel_sha256 = (
    hashlib.sha256(pathlib.Path(core_wheel_path).read_bytes()).hexdigest()
    if core_wheel_path else None
)
print("RUNTIME_WHEEL_MEMBER_INVENTORY=" + json.dumps({{
    "python_version": sys.version,
    "installed_versions": {{name: importlib.metadata.version(name) for name in (
        "actions-runtime", "actions-core", "actions-http-helper", "actions-work-items"
    )}},
    "environment_prefix": str(pathlib.Path(sys.prefix).resolve()),
    "wheel_path": str(wheel_path),
    "wheel_sha256": wheel_sha256,
    "core_wheel_path": core_wheel_path,
    "core_wheel_sha256": core_wheel_sha256,
    "runtime_direct_url": json.loads(runtime_distribution.read_text("direct_url.json") or "{{}}"),
    "modules": runtime_modules,
}}, sort_keys=True))
"""
    )
    probe += build_import_path_guard(Path(checkout))
    probe += (
        Path(__file__)
        .with_name("verify_request_boundaries.py")
        .read_text(encoding="utf-8")
    )
    try:
        subprocess.run(
            [str(python), "-c", build_import_path_guard(Path(checkout))],
            check=True,
            capture_output=True,
            text=True,
            cwd=isolated_workdir,
            env=environment,
        )
        subprocess.run(
            [str(python), "-m", "pip", "check"],
            check=True,
            cwd=isolated_workdir,
            env=environment,
        )
        probe_result = subprocess.run(
            [str(python), "-c", probe],
            check=True,
            capture_output=True,
            text=True,
            env=environment,
            cwd=isolated_workdir,
        )
    except subprocess.CalledProcessError as error:
        if error.stdout:
            print(error.stdout, end="", flush=True)
        if error.stderr:
            print(error.stderr, file=sys.stderr, end="", flush=True)
        raise
    for line in probe_result.stdout.splitlines():
        if line.startswith("RUNTIME_REQUEST_BOUNDARIES="):
            print(line, flush=True)
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
    verify_selected_runtime_origin(runtime_wheel, inventory["runtime_direct_url"])
    assert inventory["wheel_path"] == str(
        runtime_wheel.resolve()
    ), f"Runtime probe selected a different wheel: {inventory['wheel_path']}"
    if core_wheel is not None:
        assert inventory["core_wheel_path"] == str(core_wheel.resolve())
    _assert_wheel_digest(runtime_wheel, inventory["wheel_sha256"], "Runtime")
    if core_wheel is not None:
        _assert_wheel_digest(core_wheel, inventory["core_wheel_sha256"], "Core")
    environment_prefix = Path(inventory["environment_prefix"]).resolve()
    installed_members = {
        item["member"]: Path(item["path"]) for item in inventory["modules"]
    }
    assert len(installed_members) == len(
        inventory["modules"]
    ), "installed Runtime distribution contains duplicate Python member paths"
    bound_members = _assert_installed_runtime_wheel_has_no_private_core_imports(
        runtime_wheel,
        installed_members,
        prefix=environment_prefix,
        checkout=Path(checkout),
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
                "python_version": inventory["python_version"],
                "installed_versions": inventory["installed_versions"],
                "environment_prefix": str(environment_prefix),
                "runtime_wheel_path": str(runtime_wheel.resolve()),
                "runtime_wheel_sha256": inventory["wheel_sha256"],
                "runtime_direct_url": inventory["runtime_direct_url"],
                "core_wheel_path": inventory["core_wheel_path"],
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
        [str(python), "-m", "actions.server", "--help"],
        check=True,
        env=environment,
        cwd=isolated_workdir,
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
        cwd=isolated_workdir,
    )

    return inventory


def verify_installed(
    python: Path, isolated_workdir: Path, report_path: Path, wheel: Path
) -> None:
    public_packages = verify_public_package_report(report_path)
    oauth_hashes = verify_oauth_input_binding(
        wheel, Path(__file__).resolve().parents[1]
    )
    inventory = verify_installed_runtime_wheel(
        python, wheel, isolated_workdir, REPO_ROOT
    )
    versions = inventory["installed_versions"]
    if (
        versions["actions-core"] != EXPECTED_CORE
        or versions["actions-http-helper"] != EXPECTED_HELPER
    ):
        raise RuntimeError(
            "Installed Core or Helper version differs from the public floor"
        )
    print(
        "Verified uncached PyPI Runtime dependency artifacts: "
        + json.dumps(public_packages, sort_keys=True)
    )
    print("RUNTIME_WHEEL_OAUTH_INPUTS=" + json.dumps(oauth_hashes, sort_keys=True))
    subprocess.run(
        [str(python), "-m", "actions.server", "version"],
        check=True,
        cwd=isolated_workdir,
        env=isolated_environment(),
    )


def main(arguments: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wheel_directory", nargs="?", type=Path)
    parser.add_argument("--installed-wheel", type=Path)
    parser.add_argument("--checkout-root", type=Path)
    args = parser.parse_args(arguments)
    if args.installed_wheel is not None:
        if args.wheel_directory is not None or args.checkout_root is None:
            parser.error("--installed-wheel requires --checkout-root and no directory")
        wheel = args.installed_wheel.resolve()
        validate_runtime_metadata(wheel)
        project = args.checkout_root.resolve()
        oauth_hashes = verify_oauth_input_binding(wheel, project)
        with tempfile.TemporaryDirectory(prefix="runtime-installed-wheel-") as temp:
            workdir = Path(temp)
            verify_installed_runtime_wheel(
                Path(sys.executable), wheel, workdir, source_checkout_root(project)
            )
            subprocess.run(
                [sys.executable, "-m", "actions.server", "version"],
                check=True,
                cwd=workdir,
                env=isolated_environment(),
            )
        print("RUNTIME_WHEEL_OAUTH_INPUTS=" + json.dumps(oauth_hashes, sort_keys=True))
        return
    if args.wheel_directory is None or args.checkout_root is not None:
        parser.error(
            "provide a wheel directory or --installed-wheel with --checkout-root"
        )
    wheel = select_runtime_wheel(args.wheel_directory)
    with tempfile.TemporaryDirectory(prefix="runtime-registry-floor-") as temp:
        workdir = Path(temp)
        env_dir = workdir / "venv"
        subprocess.run(
            [sys.executable, "-m", "venv", str(env_dir)],
            check=True,
            env=isolated_environment(),
        )
        python = env_dir / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        report = workdir / "pip-install-report.json"
        subprocess.run(
            install_command(python, wheel, report),
            check=True,
            cwd=workdir,
            env=isolated_environment(),
        )
        verify_installed(python, workdir, report, wheel)


if __name__ == "__main__":
    main()
