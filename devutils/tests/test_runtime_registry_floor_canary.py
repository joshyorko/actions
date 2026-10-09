import importlib.util
import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).parents[2]
SCRIPT = ROOT / "action_server/scripts/verify_published_runtime_floor.py"
WORKFLOWS = ROOT / ".github/workflows"
spec = importlib.util.spec_from_file_location("runtime_registry_floor", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def _wheel(directory, name, version, filename=None):
    path = directory / (
        filename or f"actions_runtime-{version}-cp312-cp312-manylinux_2_17_x86_64.whl"
    )
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(
            f"actions_runtime-{version}.dist-info/METADATA",
            f"Metadata-Version: 2.1\nName: {name}\nVersion: {version}\n",
        )
    return path


def _pip_report(overrides=None):
    packages = module.EXPECTED_PUBLIC_PACKAGES
    overrides = overrides or {}
    install = []
    for name, expected in packages.items():
        item = {
            "metadata": {"name": name, "version": expected["version"]},
            "download_info": {
                "url": expected["url"],
                "archive_info": {"hashes": {"sha256": expected["sha256"]}},
            },
        }
        item.update(overrides.get(name, {}))
        install.append(item)
    return {"install": install}


def test_selects_one_cp312_runtime_wheel(tmp_path):
    expected = _wheel(tmp_path, "actions-runtime", "1.0.3")
    _wheel(
        tmp_path,
        "actions-runtime",
        "1.0.3",
        "actions_runtime-1.0.3-cp313-cp313-manylinux_2_17_x86_64.whl",
    )
    assert module.select_runtime_wheel(tmp_path) == expected


def test_rejects_wrong_runtime_version(tmp_path):
    _wheel(tmp_path, "actions-runtime", "1.0.2")
    with pytest.raises(ValueError, match="Unexpected Runtime version"):
        module.select_runtime_wheel(tmp_path)


def test_rejects_non_runtime_distribution(tmp_path):
    _wheel(tmp_path, "actions-core", "1.0.3")
    with pytest.raises(ValueError, match="Unexpected distribution"):
        module.select_runtime_wheel(tmp_path)


def test_rejects_ambiguous_cp312_wheel_inventory(tmp_path):
    _wheel(tmp_path, "actions-runtime", "1.0.3")
    _wheel(
        tmp_path,
        "actions-runtime",
        "1.0.3",
        "actions_runtime-1.0.3-cp312-abi3-manylinux_2_17_x86_64.whl",
    )
    with pytest.raises(ValueError, match="exactly one cp312"):
        module.select_runtime_wheel(tmp_path)


@pytest.mark.parametrize(
    "checkout_path",
    ["action_server/src", "actions/src", "actions-http-helper/src"],
)
def test_rejects_sys_path_leak_from_each_monorepo_package(tmp_path, checkout_path):
    source_path = tmp_path / "repo" / checkout_path
    source_path.mkdir(parents=True)
    with pytest.raises(RuntimeError, match="source checkout"):
        module.assert_no_checkout_imports(tmp_path / "repo", [str(source_path)], {})


@pytest.mark.parametrize(
    "checkout_path",
    [
        "action_server/src/actions",
        "actions/src/actions",
        "actions-http-helper/src/actions_http",
    ],
)
def test_rejects_module_origin_from_each_monorepo_package(tmp_path, checkout_path):
    source_path = tmp_path / "repo" / checkout_path / "__init__.py"
    source_path.parent.mkdir(parents=True)
    source_path.touch()
    with pytest.raises(RuntimeError, match="source checkout"):
        module.assert_no_checkout_imports(
            tmp_path / "repo", [], {"leaked": str(source_path)}
        )


def test_isolated_environment_removes_python_path_overrides():
    source = {
        "PATH": "/usr/bin",
        "PYTHONPATH": "/repo/actions/src:/repo/actions-http-helper/src",
        "PYTHONHOME": "/repo/python",
        "PYTHONUSERBASE": "/repo/user-site",
        "PYTHONSTARTUP": "/repo/startup.py",
    }
    actual = module.isolated_environment(source)
    assert actual == {"PATH": "/usr/bin", "PYTHONNOUSERSITE": "1"}


def _run_child_path_guard(repository, cwd, pythonpath=None, python=sys.executable):
    environment = dict(os.environ)
    environment.pop("PYTHONHOME", None)
    environment.pop("PYTHONUSERBASE", None)
    environment.pop("PYTHONSTARTUP", None)
    if pythonpath is None:
        environment.pop("PYTHONPATH", None)
    else:
        environment["PYTHONPATH"] = pythonpath
    return subprocess.run(
        [str(python), "-c", module.build_import_path_guard(repository)],
        cwd=cwd,
        env=environment,
        capture_output=True,
        text=True,
    )


def test_child_guard_accepts_external_workdir_without_checkout_paths(tmp_path):
    environment = module.isolated_environment()
    venv = tmp_path / "venv"
    subprocess.run(
        [sys.executable, "-m", "venv", "--without-pip", str(venv)],
        check=True,
        env=environment,
    )
    python = venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    result = _run_child_path_guard(ROOT, tmp_path, python=python)
    assert result.returncode == 0, result.stderr


def test_child_guard_rejects_checkout_as_current_directory():
    result = _run_child_path_guard(ROOT, ROOT)
    assert result.returncode != 0
    assert "source checkout" in result.stderr


def test_child_guard_rejects_relative_pythonpath_into_checkout(tmp_path):
    source = ROOT / "actions/src"
    relative_source = os.path.relpath(source, tmp_path)
    result = _run_child_path_guard(ROOT, tmp_path, relative_source)
    assert result.returncode != 0
    assert "source checkout" in result.stderr


def test_child_guard_rejects_symlink_pythonpath_into_checkout(tmp_path):
    link = tmp_path / "linked-helper-source"
    try:
        link.symlink_to(ROOT / "actions-http-helper/src", target_is_directory=True)
    except OSError as error:
        pytest.skip(f"directory symlinks are unavailable: {error}")
    result = _run_child_path_guard(ROOT, tmp_path, str(link))
    assert result.returncode != 0
    assert "source checkout" in result.stderr


def test_accepts_only_exact_public_core_and_helper_wheels(tmp_path):
    report = tmp_path / "pip-report.json"
    report.write_text(json.dumps(_pip_report()))
    actual = module.verify_public_package_report(report)
    assert actual == {
        name: {
            "version": expected["version"],
            "url": expected["url"],
            "sha256": expected["sha256"],
        }
        for name, expected in module.EXPECTED_PUBLIC_PACKAGES.items()
    }


def test_reads_utf8_pip_report_independent_of_windows_locale(tmp_path):
    report_data = _pip_report()
    report_data["install"].append(
        {
            "metadata": {"name": "unrelated-\u038f", "version": "1.0"},
            "download_info": {},
        }
    )
    report = tmp_path / "pip-report.json"
    report.write_text(json.dumps(report_data, ensure_ascii=False), encoding="utf-8")
    assert set(module.verify_public_package_report(report)) == set(
        module.EXPECTED_PUBLIC_PACKAGES
    )


@pytest.mark.parametrize(
    "name,change,error",
    [
        (
            "actions-core",
            {"url": "https://example.invalid/core.whl"},
            "public PyPI wheel URL",
        ),
        ("actions-http-helper", {"sha256": "0" * 64}, "SHA-256"),
    ],
)
def test_rejects_wrong_public_origin_or_artifact_digest(tmp_path, name, change, error):
    report_data = _pip_report()
    item = next(
        item for item in report_data["install"] if item["metadata"]["name"] == name
    )
    if "url" in change:
        item["download_info"]["url"] = change["url"]
    if "sha256" in change:
        item["download_info"]["archive_info"]["hashes"]["sha256"] = change["sha256"]
    report = tmp_path / "pip-report.json"
    report.write_text(json.dumps(report_data))
    with pytest.raises(RuntimeError, match=error):
        module.verify_public_package_report(report)


def test_rejects_report_missing_one_required_public_artifact(tmp_path):
    report_data = _pip_report()
    report_data["install"].pop()
    report = tmp_path / "pip-report.json"
    report.write_text(json.dumps(report_data))
    with pytest.raises(RuntimeError, match="omits required public packages"):
        module.verify_public_package_report(report)


def test_install_command_forces_uncached_public_pypi_resolution(tmp_path):
    command = module.install_command(
        Path("/tmp/venv/bin/python"),
        tmp_path / "runtime.whl",
        tmp_path / "report.json",
    )
    assert "--no-cache-dir" in command
    assert "--isolated" in command
    assert command[command.index("--index-url") + 1] == "https://pypi.org/simple"
    assert command[command.index("--report") + 1] == str(tmp_path / "report.json")


def test_runtime_release_workflow_runs_canary_on_community_and_integration_prs():
    workflow = yaml.safe_load(
        (WORKFLOWS / "actions_runtime_pypi_release.yml").read_text()
    )
    on = workflow.get("on", workflow.get(True))
    assert on["pull_request"]["branches"] == ["community", "integration/**"]
    steps = workflow["jobs"]["build-wheels"]["steps"]
    canary_index = next(
        i
        for i, step in enumerate(steps)
        if step.get("name") == "Verify Runtime wheel with published Core and Helper"
    )
    canary = steps[canary_index]
    assert canary["if"] == "github.event_name == 'pull_request'"
    assert "verify_published_runtime_floor.py wheelhouse" in canary["run"]
    assert canary_index > next(
        i
        for i, step in enumerate(steps)
        if step.get("name") == "Build and clean-test wheels"
    )
    assert canary_index < next(
        i for i, step in enumerate(steps) if "Upload artifact" in step.get("name", "")
    )
    publish_steps = workflow["jobs"]["publish"]["steps"]
    token_check = next(
        step
        for step in publish_steps
        if step.get("name") == "Check Runtime publish credential"
    )
    upload = next(
        step
        for step in publish_steps
        if step.get("name") == "Publish verified artifacts"
    )
    assert token_check["if"] == "github.event_name == 'push'"
    assert (
        upload["if"]
        == "github.event_name == 'push' && steps.runtime-token.outputs.enabled == 'true'"
    )
