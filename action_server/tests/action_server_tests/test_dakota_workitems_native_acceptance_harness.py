"""Deterministic admission tests for the Dakota native acceptance receipt."""

from __future__ import annotations

import copy
import importlib.util
import json
import os
import shlex
import subprocess
import sys
import textwrap
import time
import zipfile
from pathlib import Path

import pytest

from actions.server._action_package_handler import ActionPackageHandler

RUNNER_PATH = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "dakota_workitems_native_acceptance.py"
)
SPEC = importlib.util.spec_from_file_location(
    "dakota_workitems_native_acceptance", RUNNER_PATH
)
assert SPEC is not None and SPEC.loader is not None
RUNNER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RUNNER)
NATIVE_TEST_PATH = Path(__file__).with_name(
    "test_dakota_workitems_native_acceptance.py"
)
NATIVE_TEST_SPEC = importlib.util.spec_from_file_location(
    "dakota_workitems_native_case", NATIVE_TEST_PATH
)
assert NATIVE_TEST_SPEC is not None and NATIVE_TEST_SPEC.loader is not None
NATIVE_TEST = importlib.util.module_from_spec(NATIVE_TEST_SPEC)
NATIVE_TEST_SPEC.loader.exec_module(NATIVE_TEST)
UI_TEST_PATH = Path(__file__).with_name("test_dakota_workitems_native_ui_acceptance.py")
CORE_VERSION = "1.0.2"


def _collect_nodeids(test_path: Path, *, marker: str | None = None):
    command = [
        sys.executable,
        "-m",
        "pytest",
        "--collect-only",
        "-q",
        "-p",
        "no:cacheprovider",
    ]
    if marker is not None:
        command.extend(["-m", marker])
    command.append(str(test_path))
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        command,
        cwd=NATIVE_TEST_PATH.parents[1],
        env=environment,
        capture_output=True,
        text=True,
        timeout=60,
    )


def test_native_artifact_cases_are_selected_only_by_their_exact_artifact_gate():
    generic_marker = "integration_test and not native_artifact_test"
    generic_consumer = _collect_nodeids(NATIVE_TEST_PATH, marker=generic_marker)
    assert generic_consumer.returncode == 5, (
        generic_consumer.stdout + generic_consumer.stderr
    )
    assert "test_packaged_runtime_executes_work_item_consumer_lifecycle" not in (
        generic_consumer.stdout + generic_consumer.stderr
    )

    dedicated_consumer = _collect_nodeids(NATIVE_TEST_PATH, marker="integration_test")
    assert dedicated_consumer.returncode == 0, (
        dedicated_consumer.stdout + dedicated_consumer.stderr
    )
    for suffix in RUNNER.CASE_SUFFIX.values():
        assert suffix in dedicated_consumer.stdout

    generic_ui = _collect_nodeids(UI_TEST_PATH, marker=generic_marker)
    assert generic_ui.returncode == 5, generic_ui.stdout + generic_ui.stderr
    assert (
        "test_packaged_work_items_ui_create_keyboard_narrow_and_storage_recovery"
        not in (generic_ui.stdout + generic_ui.stderr)
    )

    dedicated_ui = _collect_nodeids(UI_TEST_PATH)
    assert dedicated_ui.returncode == 0, dedicated_ui.stdout + dedicated_ui.stderr
    assert (
        "test_packaged_work_items_ui_create_keyboard_narrow_and_storage_recovery"
        in (dedicated_ui.stdout)
    )


def reports_for(
    *kinds: str, call_outcome: str = "passed"
) -> list[tuple[str, str, str]]:
    reports = []
    for kind in kinds:
        suffix = RUNNER.CASE_SUFFIX[kind]
        nodeid = (
            "tests/action_server_tests/"
            "test_dakota_workitems_native_acceptance.py::"
            "test_packaged_runtime_executes_work_item_consumer_lifecycle"
            f"{suffix}"
        )
        for phase in ("setup", "call", "teardown"):
            outcome = call_outcome if phase == "call" else "passed"
            reports.append((nodeid, phase, outcome))
    return reports


def proof_record(
    kind: str, executable_hash: str, wheel_hash: str, core_version: str = CORE_VERSION
) -> dict:
    return {
        "schema_version": 2,
        "runtime_kind": kind,
        "executable_sha256": executable_hash,
        "actions_core_wheel_sha256": wheel_hash,
        "actions_core_installation": {
            "actions_core_version": core_version,
            "actions_module_owned_by_distribution": True,
            "install_source_matches_candidate": True,
            "wheel_sha256": wheel_hash,
            "pip_report_sha256": "d" * 64,
        },
        "consumer_actions": copy.deepcopy(RUNNER.CONSUMER_ACTIONS),
        "api_state_readbacks": copy.deepcopy(RUNNER.API_STATE_READBACKS),
    }


def write_proofs(
    directory: Path,
    executable_hashes: dict[str, str],
    wheel_hash: str,
    core_version: str = CORE_VERSION,
) -> None:
    for kind in RUNNER.CASE_ENV:
        (directory / f"{kind}.json").write_text(
            json.dumps(
                proof_record(kind, executable_hashes[kind], wheel_hash, core_version)
            ),
            encoding="utf-8",
        )


def write_core_wheel(wheel: Path, version: str) -> None:
    wheel.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr(
            f"actions_core-{version}.dist-info/METADATA",
            f"Metadata-Version: 2.1\nName: actions-core\nVersion: {version}\n",
        )


def test_candidate_wheel_inventory_uses_metadata_version_and_rejects_stale_entries(
    tmp_path: Path,
):
    wheel_dir = tmp_path / "wheels"
    wheel_dir.mkdir()
    wheel = wheel_dir / "actions_core-1.0.3-py3-none-any.whl"
    write_core_wheel(wheel, "1.0.3")

    selected, version = RUNNER.inspect_core_wheel(wheel_dir)
    assert selected == wheel
    assert version == "1.0.3"

    proof_dir = tmp_path / "proofs"
    proof_dir.mkdir()
    executable_hashes = {"frozen": "a" * 64, "go-wrapper": "b" * 64}
    wheel_hash = RUNNER.sha256(wheel)
    write_proofs(proof_dir, executable_hashes, wheel_hash, version)
    assert set(
        RUNNER.validate_case_proofs(proof_dir, executable_hashes, wheel_hash, version)
    ) == set(RUNNER.CASE_ENV)
    write_proofs(proof_dir, executable_hashes, wheel_hash, CORE_VERSION)
    with pytest.raises(
        RUNNER.AcceptanceFailure,
        match="proof_core_installation_invalid_frozen",
    ):
        RUNNER.validate_case_proofs(proof_dir, executable_hashes, wheel_hash, version)

    (wheel_dir / "actions_core-1.0.2-py3-none-any.whl").write_bytes(b"stale")
    with pytest.raises(RUNNER.AcceptanceFailure, match="core_wheel_inventory_invalid"):
        RUNNER.inspect_core_wheel(wheel_dir)


def test_native_workflow_builds_candidate_version_without_reusing_wheel_output():
    workflow = (
        NATIVE_TEST_PATH.parents[3]
        / ".github"
        / "workflows"
        / "frontend-build-unauthenticated.yml"
    ).read_text(encoding="utf-8")

    assert "wheel_dir.mkdir(parents=True, exist_ok=False)" in workflow
    assert 'expected_version = package["tool"]["poetry"]["version"]' in workflow
    assert "assert len(entries) == len(wheels) == 1" in workflow
    assert 'assert metadata.get("Version") == expected_version' in workflow
    assert "actions_core-1.0.2-py3-none-any.whl" not in workflow


def test_rejects_a_single_selected_native_case():
    with pytest.raises(RUNNER.AcceptanceFailure, match="pytest_case_set_incomplete"):
        RUNNER.validate_pytest_reports(0, reports_for("frozen"))


def test_rejects_duplicate_pytest_case_reports():
    reports = reports_for("frozen", "go-wrapper")
    reports.append(reports[1])
    with pytest.raises(
        RUNNER.AcceptanceFailure, match="duplicate_pytest_report_frozen"
    ):
        RUNNER.validate_pytest_reports(0, reports)


def test_rejects_skipped_case_even_when_pytest_exits_successfully():
    reports = reports_for("frozen", "go-wrapper", call_outcome="passed")
    reports[4] = (reports[4][0], "call", "skipped")
    with pytest.raises(
        RUNNER.AcceptanceFailure, match="pytest_case_not_passed_go-wrapper"
    ):
        RUNNER.validate_pytest_reports(0, reports)


def test_fresh_proof_workspace_does_not_reuse_stale_files(tmp_path: Path):
    stale_workspace = tmp_path / "stale"
    stale_workspace.mkdir()
    (stale_workspace / "frozen.json").write_text("stale", encoding="utf-8")

    with RUNNER.fresh_proof_workspace(tmp_path) as fresh_workspace:
        assert fresh_workspace != stale_workspace
        assert list(fresh_workspace.iterdir()) == []


def test_case_proof_is_atomically_replaced_without_temp_file_residue(tmp_path: Path):
    proof_path = NATIVE_TEST._write_atomic_proof(tmp_path, "frozen", {"sequence": 1})
    assert json.loads(proof_path.read_text(encoding="utf-8")) == {"sequence": 1}

    NATIVE_TEST._write_atomic_proof(tmp_path, "frozen", {"sequence": 2})
    assert json.loads(proof_path.read_text(encoding="utf-8")) == {"sequence": 2}
    assert {path.name for path in tmp_path.iterdir()} == {"frozen.json"}


def test_rejects_missing_or_duplicate_proof_files(tmp_path: Path):
    hashes = {"frozen": "a" * 64, "go-wrapper": "b" * 64}
    wheel_hash = "c" * 64
    write_proofs(tmp_path, hashes, wheel_hash)
    (tmp_path / "go-wrapper.json").unlink()
    with pytest.raises(
        RUNNER.AcceptanceFailure, match="proof_file_set_incomplete_or_duplicate"
    ):
        RUNNER.validate_case_proofs(tmp_path, hashes, wheel_hash, CORE_VERSION)

    write_proofs(tmp_path, hashes, wheel_hash)
    (tmp_path / "frozen-copy.json").write_text("{}", encoding="utf-8")
    with pytest.raises(
        RUNNER.AcceptanceFailure, match="proof_file_set_incomplete_or_duplicate"
    ):
        RUNNER.validate_case_proofs(tmp_path, hashes, wheel_hash, CORE_VERSION)


@pytest.mark.parametrize(
    ("field", "value", "failure"),
    [
        ("runtime_kind", "go-wrapper", "proof_identity_frozen"),
        ("executable_sha256", "f" * 64, "proof_executable_hash_mismatch_frozen"),
        (
            "actions_core_wheel_sha256",
            "f" * 64,
            "proof_core_installation_invalid_frozen",
        ),
    ],
)
def test_rejects_mismatched_proof_binding(
    tmp_path: Path, field: str, value: str, failure: str
):
    hashes = {"frozen": "a" * 64, "go-wrapper": "b" * 64}
    wheel_hash = "c" * 64
    write_proofs(tmp_path, hashes, wheel_hash)
    proof_path = tmp_path / "frozen.json"
    proof = json.loads(proof_path.read_text(encoding="utf-8"))
    proof[field] = value
    proof_path.write_text(json.dumps(proof), encoding="utf-8")

    with pytest.raises(RUNNER.AcceptanceFailure, match=failure):
        RUNNER.validate_case_proofs(tmp_path, hashes, wheel_hash, CORE_VERSION)


def test_rejects_core_install_proof_bound_to_different_candidate(tmp_path: Path):
    hashes = {"frozen": "a" * 64, "go-wrapper": "b" * 64}
    wheel_hash = "c" * 64
    write_proofs(tmp_path, hashes, wheel_hash)
    proof_path = tmp_path / "frozen.json"
    proof = json.loads(proof_path.read_text(encoding="utf-8"))
    proof["actions_core_installation"]["wheel_sha256"] = "e" * 64
    proof_path.write_text(json.dumps(proof), encoding="utf-8")

    with pytest.raises(
        RUNNER.AcceptanceFailure, match="proof_core_installation_invalid_frozen"
    ):
        RUNNER.validate_case_proofs(tmp_path, hashes, wheel_hash, CORE_VERSION)


def test_incomplete_pytest_run_cannot_finalize_pass(tmp_path: Path):
    hashes = {"frozen": "a" * 64, "go-wrapper": "b" * 64}
    wheel_hash = "c" * 64
    write_proofs(tmp_path, hashes, wheel_hash)
    receipt = {
        "status": "IN_PROGRESS",
        "cases": [{"kind": kind, "status": "READY"} for kind in hashes],
    }

    with pytest.raises(RUNNER.AcceptanceFailure):
        RUNNER.finalize_success(
            receipt,
            0,
            reports_for("frozen"),
            tmp_path,
            hashes,
            wheel_hash,
            CORE_VERSION,
        )

    assert receipt["status"] != "PASS"
    assert "pytest_output" not in receipt


def test_acceptance_claims_are_not_presented_as_build_provenance():
    receipt = RUNNER.initial_receipt("a" * 40, "dakota-local", CORE_VERSION)

    assert receipt["source_sha_claim"] == "a" * 40
    assert receipt["build_version_claim"] == "dakota-local"
    assert receipt["build_claim_verification"] == (
        "caller supplied; not verified against a retained build manifest"
    )
    assert "source_sha" not in receipt
    assert "build_output" not in receipt


def test_native_package_yaml_replaces_core_with_measured_wheel_after_rcc_install(
    tmp_path: Path,
):
    processor_path = tmp_path / "dakota_workitems_processor.py"
    processor_path.write_text(NATIVE_TEST.PROCESSOR_ACTION, encoding="utf-8")
    spec = importlib.util.spec_from_file_location(
        "dakota_workitems_generated_processor", processor_path
    )
    assert spec is not None and spec.loader is not None
    processor_module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = processor_module
    try:
        spec.loader.exec_module(processor_module)
    finally:
        sys.modules.pop(spec.name, None)
    assert callable(processor_module.process_work_item)

    wheel = tmp_path / "candidate wheels" / "actions_core-1.0.2-py3-none-any.whl"
    wheel.parent.mkdir()
    wheel.write_bytes(b"candidate core wheel")
    package = tmp_path / "consumer package"
    package.mkdir()
    report = package / "core install report.json"
    package_yaml = package / "package.yaml"
    package_yaml.write_text(
        NATIVE_TEST.consumer_package_yaml(wheel, report), encoding="utf-8"
    )

    handler = ActionPackageHandler(str(package), tmp_path / "data")
    contents = handler.package_yaml_contents
    assert contents is not None
    assert contents["spec-version"] == "v2"
    assert contents["dependencies"]["conda-forge"] == ["python=3.12", "uv=0.9.26"]
    assert contents["dependencies"]["pypi"] == ["actions-work-items=0.4.4"]
    assert handler.get_pythonpath_entries() == (".",)
    post_install = contents["post-install"]
    assert len(post_install) == 1
    expected_install_args = [
        "python",
        "-m",
        "pip",
        "install",
        "--force-reinstall",
        "--report",
        report.resolve().as_posix(),
        wheel.resolve().as_posix(),
    ]
    if os.name == "nt":
        assert post_install[0] == subprocess.list2cmdline(expected_install_args)
    else:
        assert shlex.split(post_install[0]) == expected_install_args


def test_consumer_resolves_candidate_wheel_file_url_on_native_platform(tmp_path: Path):
    wheel = tmp_path / "wheel with spaces" / "actions_core-1.0.2.whl"
    wheel.parent.mkdir()

    assert (
        NATIVE_TEST._local_wheel_path_from_file_url(wheel.as_uri()) == wheel.resolve()
    )


def test_consumer_rejects_nonlocal_candidate_wheel_url():
    with pytest.raises(ValueError, match="not a local file URL"):
        NATIVE_TEST._local_wheel_path_from_file_url("https://example.test/core.whl")


def test_build_manifest_binds_source_platform_paths_and_measured_bytes(
    tmp_path: Path, monkeypatch
):
    package = tmp_path / "action_server"
    suffix = ".exe" if RUNNER.platform.system() == "Windows" else ""
    frozen = package / "dist" / "action-server" / f"action-server{suffix}"
    wrapper = package / "dist" / "final" / f"action-server{suffix}"
    frozen.parent.mkdir(parents=True)
    wrapper.parent.mkdir(parents=True)
    frozen.write_bytes(b"frozen bytes")
    wrapper.write_bytes(b"go bytes")
    executables = {"frozen": frozen, "go-wrapper": wrapper}
    hashes = {kind: RUNNER.sha256(path) for kind, path in executables.items()}
    manifest = {
        "schema_version": 1,
        "source_sha": "a" * 40,
        "platform": RUNNER.platform.system(),
        "architecture": RUNNER.platform.machine(),
        "artifacts": {
            kind: {
                "path": path.relative_to(package).as_posix(),
                "sha256": hashes[kind],
            }
            for kind, path in executables.items()
        },
    }
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    result = RUNNER.validate_build_manifest(
        manifest_path, package, "a" * 40, executables, hashes
    )

    assert result["manifest_sha256"] == RUNNER.sha256(manifest_path)
    assert result["source_sha"] == "a" * 40


@pytest.mark.parametrize(
    ("mutation", "failure"),
    [
        ("source_sha", "build_manifest_source_sha_mismatch"),
        ("platform", "build_manifest_platform_mismatch"),
        ("architecture", "build_manifest_architecture_mismatch"),
        ("path", "build_manifest_artifact_path_mismatch_frozen"),
        ("sha256", "build_manifest_artifact_hash_mismatch_frozen"),
    ],
)
def test_build_manifest_rejects_unbound_claims(tmp_path, mutation, failure):
    package = tmp_path / "action_server"
    suffix = ".exe" if RUNNER.platform.system() == "Windows" else ""
    frozen = package / "dist" / "action-server" / f"action-server{suffix}"
    wrapper = package / "dist" / "final" / f"action-server{suffix}"
    frozen.parent.mkdir(parents=True)
    wrapper.parent.mkdir(parents=True)
    frozen.write_bytes(b"frozen bytes")
    wrapper.write_bytes(b"go bytes")
    executables = {"frozen": frozen, "go-wrapper": wrapper}
    hashes = {kind: RUNNER.sha256(path) for kind, path in executables.items()}
    manifest = {
        "schema_version": 1,
        "source_sha": "a" * 40,
        "platform": RUNNER.platform.system(),
        "architecture": RUNNER.platform.machine(),
        "artifacts": {
            kind: {
                "path": path.relative_to(package).as_posix(),
                "sha256": hashes[kind],
            }
            for kind, path in executables.items()
        },
    }
    if mutation == "source_sha":
        manifest["source_sha"] = "b" * 40
    elif mutation == "platform":
        manifest["platform"] = "other-platform"
    elif mutation == "architecture":
        manifest["architecture"] = "other-architecture"
    elif mutation == "path":
        manifest["artifacts"]["frozen"]["path"] = "elsewhere/action-server"
    else:
        manifest["artifacts"]["frozen"]["sha256"] = "f" * 64
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(RUNNER.AcceptanceFailure, match=failure):
        RUNNER.validate_build_manifest(
            manifest_path, package, "a" * 40, executables, hashes
        )


def test_abrupt_process_termination_invalidates_previous_pass(tmp_path: Path):
    """A killed in-flight runner cannot leave yesterday's PASS at the receipt path."""
    frozen = tmp_path / "frozen"
    wrapper = tmp_path / "wrapper"
    frozen.write_bytes(b"frozen artifact")
    wrapper.write_bytes(b"wrapper artifact")
    rcc_home = tmp_path / "rcc"
    wheel = rcc_home / "wheels" / "actions_core-1.0.2-py3-none-any.whl"
    wheel.parent.mkdir(parents=True)
    write_core_wheel(wheel, CORE_VERSION)

    receipt_path = tmp_path / "receipt.json"
    receipt_path.write_text(
        json.dumps(
            {"schema_version": 2, "attempt_id": "old-attempt", "status": "PASS"}
        ),
        encoding="utf-8",
    )
    pytest_entered = tmp_path / "pytest-entered"
    child = tmp_path / "runner_child.py"
    child.write_text(
        textwrap.dedent(
            """
            import importlib.util
            import os
            import sys
            import threading
            from pathlib import Path

            runner_path = Path(os.environ["RUNNER_PATH"])
            spec = importlib.util.spec_from_file_location("acceptance_runner", runner_path)
            runner = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(runner)
            sys.argv = [
                "acceptance",
                "--frozen", os.environ["FROZEN"],
                "--go-wrapper", os.environ["WRAPPER"],
                "--rcc-home", os.environ["RCC_HOME"],
                "--receipt", os.environ["RECEIPT"],
                "--source-sha", "a" * 40,
                "--build-version", "test",
            ]

            class BlockingPytest:
                def main(self, args, plugins):
                    Path(os.environ["PYTEST_ENTERED"]).write_text("entered", encoding="utf-8")
                    threading.Event().wait()

            sys.modules["pytest"] = BlockingPytest()
            runner.main()
            """
        ),
        encoding="utf-8",
    )
    child_env = os.environ.copy()
    child_env.update(
        {
            "RUNNER_PATH": str(RUNNER_PATH),
            "FROZEN": str(frozen),
            "WRAPPER": str(wrapper),
            "RCC_HOME": str(rcc_home),
            "RECEIPT": str(receipt_path),
            "PYTEST_ENTERED": str(pytest_entered),
        }
    )
    process = subprocess.Popen(
        [sys.executable, str(child)],
        cwd=tmp_path,
        env=child_env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline and not pytest_entered.exists():
            if process.poll() is not None:
                pytest.fail(
                    "acceptance runner exited before entering the blocking pytest shim"
                )
            time.sleep(0.02)
        assert (
            pytest_entered.is_file()
        ), "runner did not reach the controlled pytest block"

        in_progress = json.loads(receipt_path.read_text(encoding="utf-8"))
        assert in_progress["status"] == "IN_PROGRESS"
        assert in_progress["attempt_id"] != "old-attempt"

        process.terminate()
        process.wait(timeout=5)
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)

    interrupted_receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert interrupted_receipt["status"] == "IN_PROGRESS"
    assert interrupted_receipt["attempt_id"] != "old-attempt"
    assert "pytest_output" not in interrupted_receipt


@pytest.mark.parametrize("final_check", ["unchanged", "changed", "interrupted"])
def test_receipt_requires_completed_final_artifact_checks(
    tmp_path, monkeypatch, final_check
):
    """Even passed native cases cannot admit changed or unverified final artifacts."""
    monkeypatch.setattr(os, "environ", os.environ.copy())
    frozen = tmp_path / "frozen"
    wrapper = tmp_path / "wrapper"
    frozen.write_bytes(b"frozen artifact")
    wrapper.write_bytes(b"wrapper artifact")
    wheel = tmp_path / "rcc" / "wheels" / "actions_core-1.0.2-py3-none-any.whl"
    wheel.parent.mkdir(parents=True)
    write_core_wheel(wheel, CORE_VERSION)
    receipt_path = tmp_path / "receipt.json"
    hashes = {"frozen": RUNNER.sha256(frozen), "go-wrapper": RUNNER.sha256(wrapper)}
    wheel_hash = RUNNER.sha256(wheel)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "acceptance",
            "--frozen",
            str(frozen),
            "--go-wrapper",
            str(wrapper),
            "--rcc-home",
            str(wheel.parent.parent),
            "--receipt",
            str(receipt_path),
            "--source-sha",
            "a" * 40,
            "--build-version",
            "test",
        ],
    )

    def completed_native_cases(args, plugins):
        plugins[0].reports = reports_for("frozen", "go-wrapper")
        write_proofs(Path(os.environ["DAKOTA_WORKITEMS_PROOF_DIR"]), hashes, wheel_hash)
        if final_check == "changed":
            frozen.write_bytes(b"different artifact")
        elif final_check == "interrupted":

            def interrupted_hash(path):
                raise KeyboardInterrupt

            monkeypatch.setattr(RUNNER, "sha256", interrupted_hash)
        return 0

    monkeypatch.setattr(pytest, "main", completed_native_cases)
    if final_check == "interrupted":
        with pytest.raises(KeyboardInterrupt):
            RUNNER.main()
    else:
        assert RUNNER.main() == (0 if final_check == "unchanged" else 1)
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if final_check == "unchanged":
        assert receipt["status"] == "PASS"
        assert all(case["status"] == "PASS" for case in receipt["cases"])
    else:
        assert receipt["status"] == "FAIL"
        assert all(case["status"] == "NOT_VERIFIED" for case in receipt["cases"])
        assert "pytest_output" not in receipt
        assert all("api_state_readbacks" not in case for case in receipt["cases"])
