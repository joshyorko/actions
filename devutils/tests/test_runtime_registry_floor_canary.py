import hashlib
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
    expected = _wheel(tmp_path, "actions-runtime", "1.0.4")
    _wheel(
        tmp_path,
        "actions-runtime",
        "1.0.4",
        "actions_runtime-1.0.4-cp313-cp313-manylinux_2_17_x86_64.whl",
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
    _wheel(tmp_path, "actions-runtime", "1.0.4")
    _wheel(
        tmp_path,
        "actions-runtime",
        "1.0.4",
        "actions_runtime-1.0.4-cp312-abi3-manylinux_2_17_x86_64.whl",
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


def _oauth_wheel(tmp_path, *, newline=b"\n", generated_contents=None):
    project = tmp_path / "project"
    inputs = project / "oauth2"
    inputs.mkdir(parents=True)
    raw = b"formatVersion: 1.0.0\noauth2Config:\n  providers: {}\n".replace(
        b"\n", newline
    )
    pairs = {
        "actions_config": "actions-oauth-config.yaml",
        "default_user_config": "oauth-config.yaml",
    }
    for filename in pairs.values():
        (inputs / filename).write_bytes(raw)
    contents = {key: raw.decode("utf-8") for key in pairs}
    if generated_contents is not None:
        contents = generated_contents
    hashes = {
        filename: hashlib.sha256(contents[key].encode("utf-8")).hexdigest()
        for key, filename in pairs.items()
    }
    wheel = _wheel(tmp_path, "actions-runtime", "1.0.4")
    with zipfile.ZipFile(wheel, "a") as archive:
        archive.writestr(
            "actions/server/_oauth2_config.py",
            f"FILE_CONTENTS = {contents!r}\nINPUT_SHA256 = {hashes!r}\n",
        )
    return wheel, project, hashes


@pytest.mark.parametrize("newline", [b"\n", b"\r\n"])
def test_selected_wheel_oauth_binds_exact_owned_input_bytes(tmp_path, newline):
    wheel, project, hashes = _oauth_wheel(tmp_path, newline=newline)
    assert module.verify_oauth_input_binding(wheel, project) == hashes


def test_selected_wheel_oauth_rejects_self_consistent_unowned_payload(tmp_path):
    wheel, project, _ = _oauth_wheel(
        tmp_path,
        generated_contents={"actions_config": "", "default_user_config": ""},
    )
    with pytest.raises(RuntimeError, match="OAuth2.*input"):
        module.verify_oauth_input_binding(wheel, project)


def test_selected_wheel_oauth_rejects_executable_generated_values(tmp_path):
    wheel, project, _ = _oauth_wheel(tmp_path)
    other = tmp_path / "executable.whl"
    with zipfile.ZipFile(wheel) as source, zipfile.ZipFile(other, "w") as target:
        for name in source.namelist():
            contents = source.read(name)
            if name == "actions/server/_oauth2_config.py":
                contents = b"FILE_CONTENTS = dict()\nINPUT_SHA256 = {}\n"
            target.writestr(name, contents)
    with pytest.raises(RuntimeError, match="literal"):
        module.verify_oauth_input_binding(other, project)


def test_cibuildwheel_checks_each_final_repaired_wheel():
    workflow = yaml.safe_load(
        (WORKFLOWS / "actions_runtime_pypi_release.yml").read_text()
    )
    build = next(
        step
        for step in workflow["jobs"]["build-wheels"]["steps"]
        if step.get("name") == "Build and clean-test wheels"
    )
    assert build["env"]["CIBW_TEST_COMMAND"] == (
        'python "{project}/scripts/verify_published_runtime_floor.py" '
        '--installed-wheel "{wheel}" --checkout-root "{project}" '
        "${{ github.event_name == 'pull_request' && "
        "'--candidate-sdk-wheelhouse {project}/candidate-sdk-wheelhouse "
        "--candidate-core-wheelhouse {project}/candidate-core-wheelhouse' || '' }}"
    )
    assert set(build["env"]["CIBW_BUILD"].split()) == {
        f"cp{python}-*{platform}*{architecture}"
        for python in ("312", "313")
        for platform, architecture in (
            ("macos", "arm64"),
            ("manylinux", "x86_64"),
            ("win", "amd64"),
        )
    }


def test_installed_wheel_rejects_wrong_metadata_before_execution(tmp_path):
    wheel = _wheel(tmp_path, "actions-runtime", "1.0.2")
    with pytest.raises(ValueError, match="Unexpected Runtime version"):
        module.main(["--installed-wheel", str(wheel), "--checkout-root", str(tmp_path)])


def test_selected_wheel_origin_rejects_another_same_version_archive(tmp_path):
    wheel = _wheel(tmp_path, "actions-runtime", "1.0.4")
    direct_url = {
        "url": wheel.resolve().as_uri(),
        "archive_info": {"hashes": {"sha256": "0" * 64}},
    }
    with pytest.raises(RuntimeError, match="selected Runtime wheel"):
        module.verify_selected_runtime_origin(wheel, direct_url)


def test_selected_wheel_origin_binds_local_archive_url_and_digest(tmp_path):
    wheel = _wheel(tmp_path, "actions-runtime", "1.0.4")
    direct_url = {
        "url": wheel.resolve().as_uri(),
        "archive_info": {
            "hashes": {"sha256": hashlib.sha256(wheel.read_bytes()).hexdigest()}
        },
    }
    module.verify_selected_runtime_origin(wheel, direct_url)


def test_selected_wheel_origin_resolves_local_archive_alias(tmp_path):
    wheel = _wheel(tmp_path, "actions-runtime", "1.0.4")
    alias = tmp_path / "wheel-alias.whl"
    try:
        alias.symlink_to(wheel)
    except OSError as error:
        pytest.skip(f"file symlinks are unavailable: {error}")
    module.verify_selected_runtime_origin(
        wheel,
        {
            "url": alias.absolute().as_uri(),
            "archive_info": {
                "hashes": {"sha256": hashlib.sha256(wheel.read_bytes()).hexdigest()}
            },
        },
    )


def test_failed_real_probe_preserves_stdout_stderr_and_exit_code(
    tmp_path, monkeypatch, capsys
):
    wheel = _wheel(tmp_path, "actions-runtime", "1.0.4")
    monkeypatch.setattr(
        module,
        "build_import_path_guard",
        lambda _: (
            "import sys\n"
            "print('controlled-probe-stdout')\n"
            "print('controlled-probe-stderr', file=sys.stderr)\n"
            "raise SystemExit(23)\n"
        ),
    )
    with pytest.raises(subprocess.CalledProcessError) as failed:
        module.verify_installed_runtime_wheel(
            Path(sys.executable), wheel, tmp_path, ROOT
        )
    assert failed.value.returncode == 23
    captured = capsys.readouterr()
    assert "controlled-probe-stdout" in captured.out
    assert "controlled-probe-stderr" in captured.err


@pytest.mark.parametrize("source", ["actions/src", "actions-http-helper/src", "."])
def test_installed_mode_excludes_monorepo_sibling_search_paths(tmp_path, source):
    repository = tmp_path / "repo"
    project = repository / "action_server"
    project.mkdir(parents=True)
    (repository / "AGENTS.md").write_text("repository instructions\n")
    for sibling in ("actions/src", "actions-http-helper/src"):
        (repository / sibling).mkdir(parents=True)
    checkout = module.source_checkout_root(project)
    assert checkout == repository
    result = _run_child_path_guard(checkout, tmp_path, str(repository / source))
    assert result.returncode != 0
    assert "source checkout" in result.stderr


def test_installed_mode_keeps_isolated_package_boundary(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    checkout = module.source_checkout_root(project)
    assert checkout == project
    result = _run_child_path_guard(checkout, tmp_path)
    assert result.returncode == 0, result.stderr


def test_candidate_sdk_install_is_explicit_and_preserves_public_core_helper_pins(
    tmp_path,
):
    sdk = tmp_path / "actions_work_items-0.5.0a1-py3-none-any.whl"
    with zipfile.ZipFile(sdk, "w") as wheel:
        wheel.writestr(
            "actions_work_items-0.5.0a1.dist-info/METADATA",
            "Name: actions-work-items\nVersion: 0.5.0a1\n",
        )
    runtime = _wheel(tmp_path, "actions-runtime", "1.1.0a2")
    command = module.install_command(
        Path("/consumer/python"), runtime, tmp_path / "report.json", candidate_sdk=sdk
    )
    assert str(sdk.resolve()) in command
    assert "actions-core==1.0.2" in command
    assert "actions-http-helper==1.0.3" in command
    assert "--no-deps" not in command
    with pytest.raises(ValueError, match="Unexpected Runtime version"):
        module.validate_runtime_metadata(runtime)
    module.validate_runtime_metadata(runtime, expected_runtime="1.1.0a2")


def test_candidate_sdk_version_is_bound_to_source_and_default_runtime_stays_strict(
    tmp_path,
):
    root = tmp_path / "repo"
    project = root / "action_server"
    project.mkdir(parents=True)
    (root / "work-items").mkdir()
    (project / "pyproject.toml").write_text('[tool.poetry]\nversion="1.1.0a2"\n')
    (root / "work-items" / "pyproject.toml").write_text(
        '[project]\nversion="0.5.0a1"\n'
    )
    wheelhouse = tmp_path / "wheels"
    wheelhouse.mkdir()
    sdk = _wheel(wheelhouse, "actions-work-items", "0.5.0a1")
    assert module.select_candidate_sdk(wheelhouse, project) == (sdk, "1.1.0a2")
    sdk.unlink()
    _wheel(wheelhouse, "actions-work-items", "0.4.4")
    with pytest.raises(ValueError, match="differs from producer"):
        module.select_candidate_sdk(wheelhouse, project)


@pytest.mark.parametrize("alter", [None, "source", "sdk", "wheel", "runtime"])
def test_candidate_producer_receipt_survives_cibuildwheel_project_only_layout(
    tmp_path, monkeypatch, alter
):
    import hashlib

    project = tmp_path / "project"
    project.mkdir()
    raw = '[tool.poetry]\nversion="1.1.0a2"\n'
    (project / "pyproject.toml").write_text(raw)
    wheelhouse = project / "candidate-sdk-wheelhouse"
    wheelhouse.mkdir()
    wheel = _wheel(wheelhouse, "actions-work-items", "0.5.0a1")
    sdk = '[project]\nname="actions-work-items"\nversion="0.5.0a1"\n'
    receipt = {
        "schema": "actions.candidate-sdk-producer/v1",
        "source_sha": "a" * 40,
        "runtime_pyproject_sha256": hashlib.sha256(raw.encode()).hexdigest(),
        "sdk_pyproject": sdk,
        "sdk_pyproject_sha256": hashlib.sha256(sdk.encode()).hexdigest(),
        "wheel": {
            "filename": wheel.name,
            "sha256": hashlib.sha256(wheel.read_bytes()).hexdigest(),
        },
    }
    if alter == "source":
        receipt["source_sha"] = "b" * 40
    if alter == "sdk":
        receipt["sdk_pyproject"] += "# changed\n"
    if alter == "wheel":
        receipt["wheel"]["sha256"] = "0" * 64
    if alter == "runtime":
        receipt["runtime_pyproject_sha256"] = "0" * 64
    (wheelhouse / "producer.json").write_text(json.dumps(receipt))
    monkeypatch.setenv("ACTIONS_CANDIDATE_SOURCE_SHA", "a" * 40)
    if alter:
        with pytest.raises(ValueError, match="producer"):
            module.select_candidate_sdk(wheelhouse, project)
    else:
        assert module.select_candidate_sdk(wheelhouse, project) == (wheel, "1.1.0a2")


def test_explicit_core_candidate_does_not_relax_published_helper_or_default_floor(
    tmp_path,
):
    core = _wheel(tmp_path, "actions-core", "1.1.0a1")
    runtime = _wheel(tmp_path, "actions-runtime", "1.1.0a8")
    command = module.install_command(
        Path("/consumer/python"), runtime, tmp_path / "report.json", candidate_core=core
    )
    assert str(core.resolve()) in command
    assert "actions-core==1.0.2" not in command
    assert "actions-http-helper==1.0.3" in command
    assert module.EXPECTED_CORE == "1.0.2"
    assert module.EXPECTED_RUNTIME == "1.0.4"
    assert "actions-core==1.0.2" in module.install_command(
        Path("/consumer/python"), runtime, tmp_path / "report.json"
    )


@pytest.mark.parametrize("alter", [None, "source", "core", "wheel", "runtime"])
def test_core_candidate_producer_survives_project_only_mount(
    tmp_path, monkeypatch, alter
):
    project = tmp_path / "project"
    project.mkdir()
    raw = '[tool.poetry]\nversion="1.1.0a8"\n'
    (project / "pyproject.toml").write_text(raw)
    wheelhouse = project / "candidate-core-wheelhouse"
    wheelhouse.mkdir()
    wheel = _wheel(wheelhouse, "actions-core", "1.1.0a1")
    core = '[tool.poetry]\nname="actions-core"\nversion="1.1.0a1"\n'
    receipt = {
        "schema": "actions.candidate-core-producer/v1",
        "source_sha": "a" * 40,
        "runtime_pyproject_sha256": hashlib.sha256(raw.encode()).hexdigest(),
        "core_pyproject": core,
        "core_pyproject_sha256": hashlib.sha256(core.encode()).hexdigest(),
        "wheel": {
            "filename": wheel.name,
            "sha256": hashlib.sha256(wheel.read_bytes()).hexdigest(),
        },
    }
    if alter == "source":
        receipt["source_sha"] = "b" * 40
    if alter == "core":
        receipt["core_pyproject"] += "# changed\n"
    if alter == "wheel":
        receipt["wheel"]["sha256"] = "0" * 64
    if alter == "runtime":
        receipt["runtime_pyproject_sha256"] = "0" * 64
    (wheelhouse / "producer.json").write_text(json.dumps(receipt))
    monkeypatch.setenv("ACTIONS_CANDIDATE_SOURCE_SHA", "a" * 40)
    if alter:
        with pytest.raises(ValueError, match="producer"):
            module.select_candidate_core(wheelhouse, project)
    else:
        assert module.select_candidate_core(wheelhouse, project) == (wheel, "1.1.0a8")


def test_candidate_core_report_requires_exact_local_bytes_and_keeps_helper_pin(
    tmp_path,
):
    core = _wheel(tmp_path, "actions-core", "1.1.0a1")
    helper = module.EXPECTED_PUBLIC_PACKAGES["actions-http-helper"]
    payload = {
        "install": [
            {
                "metadata": {"name": "actions-core", "version": "1.1.0a1"},
                "download_info": {
                    "url": core.resolve().as_uri(),
                    "archive_info": {
                        "hashes": {
                            "sha256": hashlib.sha256(core.read_bytes()).hexdigest()
                        }
                    },
                },
            },
            {
                "metadata": {
                    "name": "actions-http-helper",
                    "version": helper["version"],
                },
                "download_info": {
                    "url": helper["url"],
                    "archive_info": {"hashes": {"sha256": helper["sha256"]}},
                },
            },
        ]
    }
    report = tmp_path / "report.json"
    report.write_text(json.dumps(payload))
    assert (
        module.verify_public_package_report(report, candidate_core=core)[
            "actions-core"
        ]["version"]
        == "1.1.0a1"
    )
    with pytest.raises(RuntimeError, match="version"):
        module.verify_public_package_report(report)
    payload["install"][0]["download_info"]["archive_info"]["hashes"]["sha256"] = (
        "0" * 64
    )
    report.write_text(json.dumps(payload))
    with pytest.raises(RuntimeError, match="SHA-256"):
        module.verify_public_package_report(report, candidate_core=core)
