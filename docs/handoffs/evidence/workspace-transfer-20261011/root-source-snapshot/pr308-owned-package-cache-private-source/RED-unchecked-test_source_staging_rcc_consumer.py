"""Execute explicitly staged source through the real RCC Runtime consumer."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import sqlite3
import stat
import subprocess
import sys
from pathlib import Path

import pytest


def _verify_selected_rcc_fixture(rcc_binary: Path) -> tuple[str, str]:
    """Keep legacy pins exact; explicitly selected tests share adapter admission."""
    from actions.server import _rcc_runtime_adapter

    selector = os.environ.get("ACTIONS_RUNTIME_RCC_TEST_COMPATIBILITY")
    if selector is not None:
        identity = _rcc_runtime_adapter.verify_rcc_compatibility(rcc_binary)
        assert identity is not None
        return identity.version, identity.binary_sha256
    rcc_sha256 = hashlib.sha256(rcc_binary.read_bytes()).hexdigest()
    assert (
        rcc_sha256 == "7e588c01751ca2ae15ba13ef67f2f4b7567697a5a8389737059a73936f509428"
    )
    rcc_version = subprocess.run(
        [str(rcc_binary), "--version"], capture_output=True, text=True, check=True
    ).stdout.strip()
    assert rcc_version == "v18.19.3"
    return rcc_version, rcc_sha256


def _staged_worker_evidence(handle: object, artifact_digest: str) -> dict[str, object]:
    """Retain private measured lease/cleanup facts; absent snapshots stay null."""
    from dataclasses import asdict

    from actions.server._actions_process_pool import WorkerRetirementResult
    from actions.server._common.process import ProcessTreeCleanupResult
    from actions.server._rcc_runtime_adapter import (
        RccProcessHandle,
        RccRuntimeError,
        read_receipt,
    )

    wrapper = getattr(handle, "_rcc_wrapper", None)
    if not isinstance(wrapper, RccProcessHandle):
        raise RccRuntimeError("receipt", "worker has no owned RCC wrapper")
    path = wrapper.receipt_file
    raw = path.read_bytes()
    receipt = read_receipt(path, artifact_digest)
    if path.read_bytes() != raw or json.loads(raw) != receipt:
        raise RccRuntimeError("receipt", "worker receipt changed during observation")
    retirement = getattr(handle, "_retirement_result", None)
    if retirement is not None and not isinstance(retirement, WorkerRetirementResult):
        raise RccRuntimeError("receipt", "invalid worker retirement result type")
    cleanup = wrapper.last_cleanup_result
    if cleanup is not None and not isinstance(cleanup, ProcessTreeCleanupResult):
        raise RccRuntimeError("receipt", "invalid wrapper cleanup result type")
    if (
        retirement is not None
        and retirement.cleanup is not None
        and not isinstance(retirement.cleanup, ProcessTreeCleanupResult)
    ):
        raise RccRuntimeError("receipt", "invalid retirement cleanup result type")
    return {
        "artifact_digest": artifact_digest,
        "runtime_receipt_path": str(path),
        "runtime_receipt_sha256": hashlib.sha256(raw).hexdigest(),
        "runtime_receipt": receipt,
        "retirement_result": asdict(retirement) if retirement is not None else None,
        "wrapper_cleanup_result": asdict(cleanup) if cleanup is not None else None,
    }


def _create_runtime_catalog_database(data_dir: Path):
    """Create the consumer test catalog using the complete Runtime registry."""
    from actions.server._database import Database
    from actions.server._models import get_all_model_classes, get_model_db_rules

    data_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    database = Database(data_dir / "catalog.sqlite")
    database.initialize(get_all_model_classes())
    database.create_tables(get_model_db_rules())
    return database


def test_runtime_catalog_database_fixture_creates_directory_and_current_schema(
    tmp_path: Path,
):
    """Exercise the SQLite consumer fixture without an RCC-managed environment."""
    database = _create_runtime_catalog_database(tmp_path / "runtime-data")

    assert database.db_path.is_file()
    with sqlite3.connect(database.db_path) as connection:
        # This table is part of the current registry and must be available to
        # the real staged-source consumer before package admission begins.
        table = connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            ("mcp_catalog_name",),
        ).fetchone()
    assert table == ("mcp_catalog_name",)


@pytest.mark.integration_test
@pytest.mark.real_rcc
@pytest.mark.skipif(
    sys.platform != "linux", reason="RCC publication proof requires Linux"
)
def test_published_artifact_details_preserves_one_rcc_identity_pair(tmp_path: Path):
    """Capture both canonical digests from one real RCC environment publication."""
    if os.environ.get("ACTIONS_REAL_RCC_ARTIFACT_TEST") != "1":
        pytest.skip("set ACTIONS_REAL_RCC_ARTIFACT_TEST=1 for RCC publication proof")

    from actions.server import _rcc_runtime_adapter
    from actions.server._rcc_runtime_adapter import publish_artifact_details

    rcc_value = os.environ.get("ACTIONS_RUNTIME_RCC_BINARY")
    if not rcc_value:
        pytest.fail("ACTIONS_RUNTIME_RCC_BINARY is required for RCC publication proof")
    rcc_binary = Path(rcc_value).resolve(strict=True)
    rcc_version, rcc_sha256 = _verify_selected_rcc_fixture(rcc_binary)

    package_dir = tmp_path / "minimal-package"
    package_dir.mkdir(mode=0o700)
    environment = package_dir / "package.yaml"
    environment.write_text(
        "version: 0.1\nspec-version: v2\ndependencies:\n"
        "  conda-forge:\n    - python=3.12.15\n",
        encoding="utf-8",
    )

    helper_path = (
        Path(__file__).resolve().parents[2] / "scripts/verify_dakota_rcc_acceptance.py"
    )
    helper_spec = importlib.util.spec_from_file_location(
        "rcc_details_provider_harness", helper_path
    )
    assert helper_spec is not None and helper_spec.loader is not None
    provider_harness = importlib.util.module_from_spec(helper_spec)
    helper_spec.loader.exec_module(provider_harness)
    provider_tmp = tmp_path / "provider-tmp"
    provider_home = tmp_path / "provider-home"
    provider_tmp.mkdir(mode=0o700)
    provider_home.mkdir(mode=0o700)
    provider_environment = os.environ.copy()
    provider_environment.update(
        {
            "ACTIONS_HOME": str(provider_home),
            "ROBOCORP_HOME": str(provider_home),
            "TMPDIR": str(provider_tmp),
        }
    )
    provider, provider_url = provider_harness.start_provider(
        str(rcc_binary),
        tmp_path / "selected-provider",
        provider_environment,
        deadline=provider_harness.Deadline.after(900),
    )

    invocations: list[dict[str, object]] = []

    def recording_runner(*args: str) -> tuple[int, str, str]:
        result = _rcc_runtime_adapter._subprocess_runner(*args)
        invocations.append(
            {
                "args": list(args),
                "returncode": result[0],
                "stdout": result[1],
                "stderr": result[2],
            }
        )
        return result

    try:
        details = publish_artifact_details(
            environment, rcc_binary, provider=provider_url, runner=recording_runner
        )
        assert len(invocations) == 1
        invocation = invocations[0]
        assert invocation["args"] == [
            str(rcc_binary),
            "env",
            "publish",
            "--environment",
            str(environment),
            "--json",
            "--provider",
            provider_url,
        ]
        assert invocation["returncode"] == 0
        raw_json = invocation["stdout"]
        assert isinstance(raw_json, str)
        payload = json.loads(raw_json)
        assert payload["specificationDigest"] == details.specification_digest
        assert payload["artifactDigest"] == details.artifact_digest
    finally:
        provider_harness.terminate_process_tree(provider)
        assert provider.poll() is not None

    repository_root = Path(__file__).resolve().parents[3]
    source_commit = subprocess.check_output(
        ["git", "-C", str(repository_root), "rev-parse", "HEAD"], text=True
    ).strip()
    source_tree = subprocess.check_output(
        ["git", "-C", str(repository_root), "rev-parse", "HEAD^{tree}"], text=True
    ).strip()
    assert source_commit == os.environ.get("RCC_ROLLBACK_CANDIDATE_SHA")
    assert source_tree == os.environ.get("RCC_ROLLBACK_CANDIDATE_TREE")
    control_commit = os.environ.get("RCC_ROLLBACK_CONTROL_SHA")
    control_tree = os.environ.get("RCC_ROLLBACK_CONTROL_TREE")
    assert control_commit and len(control_commit) == 40
    assert control_tree and len(control_tree) == 40

    receipt_path_value = os.environ.get("ACTIONS_RUNTIME_PUBLISHED_DETAILS_RECEIPT")
    if not receipt_path_value:
        pytest.fail("ACTIONS_RUNTIME_PUBLISHED_DETAILS_RECEIPT is required")
    receipt = {
        "schema_version": 1,
        "status": "PASS",
        "source": {"commit": source_commit, "tree": source_tree},
        "control": {"commit": control_commit, "tree": control_tree},
        "rcc": {"version": rcc_version, "sha256": rcc_sha256},
        "publication": {
            "invocation_count": len(invocations),
            "provider": provider_url,
            "args": invocation["args"],
            "specification_digest": details.specification_digest,
            "artifact_digest": details.artifact_digest,
            "raw_json": raw_json,
            "raw_json_sha256": hashlib.sha256(raw_json.encode("utf-8")).hexdigest(),
        },
    }
    receipt_path = Path(receipt_path_value)
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


@pytest.mark.integration_test
@pytest.mark.real_rcc
@pytest.mark.skipif(sys.platform != "linux", reason="source staging requires Linux")
def test_staged_package_executes_in_managed_rcc_runtime(tmp_path: Path, monkeypatch):
    """Consume the exact staged bytes through RCC and verify worker provenance."""
    if os.environ.get("ACTIONS_REAL_RCC_ARTIFACT_TEST") != "1":
        pytest.skip("set ACTIONS_REAL_RCC_ARTIFACT_TEST=1 for staged RCC proof")

    rcc_binary_value = os.environ.get("ACTIONS_RUNTIME_RCC_BINARY")
    if not rcc_binary_value:
        pytest.fail("ACTIONS_RUNTIME_RCC_BINARY is required for staged RCC proof")
    rcc_binary = Path(rcc_binary_value).resolve(strict=True)
    assert rcc_binary.is_file()
    rcc_version, rcc_sha256 = _verify_selected_rcc_fixture(rcc_binary)

    # The acceptance process owns both homes. Never inherit or mutate another
    # task's RCC cache, even when this test is run outside the hosted workflow.
    managed_home = tmp_path / "managed-home"
    runtime_tmp = tmp_path / "runtime-tmp"
    provider_tmp = tmp_path / "provider-tmp"
    for directory in (managed_home, runtime_tmp, provider_tmp):
        directory.mkdir(mode=0o700)
    monkeypatch.setenv("ACTIONS_HOME", str(managed_home))
    monkeypatch.setenv("ROBOCORP_HOME", str(managed_home))
    monkeypatch.setenv("TMPDIR", str(runtime_tmp))
    monkeypatch.setenv("ACTIONS_RUNTIME_RCC_BINARY", str(rcc_binary))
    monkeypatch.setenv("ACTIONS_REAL_RCC_ARTIFACT_TEST", "1")

    source_package = tmp_path / "selected-source"
    source_package.mkdir(mode=0o700)
    manifest_bytes = (
        b"version: 0.1\nspec-version: v2\ndependencies:\n"
        b"  conda-forge:\n    - python=3.12.15\n"
        b"  pypi:\n    - actions-core=1.0.2\n"
    )
    action_bytes = (
        "from actions import action\n"
        "import hashlib\n"
        "import actions\n"
        "import sys\n"
        "from importlib.metadata import version\n"
        "from pathlib import Path\n\n"
        "@action\n"
        "def staged_source_probe() -> dict[str, str]:\n"
        "    source = Path(__file__).resolve()\n"
        "    core = Path(actions.__file__).resolve()\n"
        "    return {\n"
        "        'action_source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),\n"
        "        'action_source_path': str(source),\n"
        "        'core_origin': str(core),\n"
        "        'core_version': version('actions-core'),\n"
        "        'python_executable': str(Path(sys.executable).resolve()),\n"
        "    }\n"
    ).encode("utf-8")
    (source_package / "package.yaml").write_bytes(manifest_bytes)
    (source_package / "action.py").write_bytes(action_bytes)

    staged_package = tmp_path / "staged-package"
    staged_package.mkdir(mode=0o700)
    source_root_fd = os.open(source_package, os.O_RDONLY | getattr(os, "O_DIRECTORY"))
    staged_root_fd = os.open(staged_package, os.O_RDONLY | getattr(os, "O_DIRECTORY"))
    try:
        from actions.server.deployments.source_staging import stage_selected_files

        staged = stage_selected_files(
            source_root_fd,
            staged_root_fd,
            ["action.py", "package.yaml"],
            protected_input_names=["package.yaml"],
        )
    finally:
        os.close(source_root_fd)
        os.close(staged_root_fd)

    source_digests = {
        "action.py": hashlib.sha256(action_bytes).hexdigest(),
        "package.yaml": hashlib.sha256(manifest_bytes).hexdigest(),
    }
    staged_entries = {entry.path: entry for entry in staged.inventory.entries}
    assert set(staged_entries) == set(source_digests)
    assert {
        name: entry.sha256 for name, entry in staged_entries.items()
    } == source_digests
    assert staged.source.inventory == staged.inventory
    assert all(
        stat.S_IMODE((staged_package / name).stat().st_mode) == 0o644
        for name in source_digests
    )

    helper_path = (
        Path(__file__).resolve().parents[2] / "scripts/verify_dakota_rcc_acceptance.py"
    )
    helper_spec = importlib.util.spec_from_file_location(
        "staged_rcc_provider_harness", helper_path
    )
    assert helper_spec is not None and helper_spec.loader is not None
    provider_harness = importlib.util.module_from_spec(helper_spec)
    helper_spec.loader.exec_module(provider_harness)
    provider_environment = os.environ.copy()
    provider_environment.update(
        {
            "ACTIONS_HOME": str(tmp_path / "provider-home"),
            "ROBOCORP_HOME": str(tmp_path / "provider-home"),
            "TMPDIR": str(provider_tmp),
        }
    )
    Path(provider_environment["ACTIONS_HOME"]).mkdir(mode=0o700)
    provider = None
    pool = None
    worker_handle = None
    worker_artifact_digest = None
    repository_root = Path(__file__).resolve().parents[3]
    source_commit = subprocess.check_output(
        ["git", "-C", str(repository_root), "rev-parse", "HEAD"], text=True
    ).strip()
    source_tree = subprocess.check_output(
        ["git", "-C", str(repository_root), "rev-parse", "HEAD^{tree}"], text=True
    ).strip()
    evidence: dict[str, object] = {
        "status": "NOT_RUN",
        "source_commit": source_commit,
        "source_tree": source_tree,
        "rcc_version": rcc_version,
        "rcc_sha256": rcc_sha256,
        "source_inventory": staged.source.inventory.canonical_json.decode("utf-8"),
        "staged_inventory": staged.inventory.canonical_json.decode("utf-8"),
        "source_sha256": source_digests,
        "staged_sha256": {name: entry.sha256 for name, entry in staged_entries.items()},
    }
    execution_passed = False
    try:
        provider, provider_url = provider_harness.start_provider(
            str(rcc_binary),
            tmp_path / "selected-provider",
            provider_environment,
            deadline=provider_harness.Deadline.after(900),
        )
        monkeypatch.setenv("ACTIONS_RUNTIME_RCC_PROVIDER", provider_url)

        import actions.server._models as models
        from actions.server._actions_import import import_action_package
        from actions.server._actions_process_pool import ActionsProcessPool
        from actions.server._models import Action, ActionPackage, Run, RunStatus
        from actions.server._rcc_runtime_adapter import load_descriptor
        from actions.server._settings import Settings

        data_dir = tmp_path / "runtime-data"
        database = _create_runtime_catalog_database(data_dir)
        with database.connect():
            models._global_db = database
            try:
                import_action_package(
                    datadir=data_dir,
                    action_package_dir=str(staged_package),
                    disable_not_imported=False,
                    skip_lint=True,
                    whitelist="",
                )
                package = database.all(ActionPackage)[0]
                action = database.all(Action)[0]
                output_schema = json.loads(action.output_schema)
                assert output_schema.get("type") == "object"
                assert output_schema.get("additionalProperties") == {"type": "string"}
                expected_result_fields = {
                    "action_source_sha256",
                    "action_source_path",
                    "core_origin",
                    "core_version",
                    "python_executable",
                }
                descriptor = load_descriptor(package.env_json)
                assert descriptor is not None
                assert descriptor.rcc_version == rcc_version
                worker_artifact_digest = descriptor.artifact_digest
                evidence["runtime_descriptor"] = descriptor.to_dict()
                assert descriptor.provider_reference == provider_url
                settings = Settings(
                    datadir=data_dir, artifacts_dir=tmp_path / "artifacts"
                )
                settings.reuse_processes = False
                settings.min_processes = 0
                settings.max_processes = 1
                pool = ActionsProcessPool(settings, {package.id: package}, [action])
                run_dir = tmp_path / "run"
                run_dir.mkdir()
                input_json = run_dir / "input.json"
                result_json = run_dir / "result.json"
                output_file = run_dir / "output.txt"
                input_json.write_text("{}", encoding="utf-8")
                run = Run(
                    id="staged-source-rcc-run",
                    status=RunStatus.NOT_RUN,
                    action_id=action.id,
                    start_time="",
                    run_time=None,
                    inputs="{}",
                    result=None,
                    error_message=None,
                    relative_artifacts_dir="",
                    numbered_id=1,
                )
                with pool.obtain_process_for_action(action) as handle:
                    worker_handle = handle
                    assert (
                        handle.run_action(
                            run,
                            package,
                            action,
                            input_json,
                            run_dir,
                            output_file,
                            result_json,
                            {},
                            {},
                            False,
                        )
                        == 0
                    )
                payload = json.loads(result_json.read_text(encoding="utf-8"))
                result = payload["result"]
                assert isinstance(result, dict)
                assert set(result) == expected_result_fields
                assert all(
                    isinstance(key, str) and isinstance(value, str)
                    for key, value in result.items()
                )
                assert result["action_source_sha256"] == source_digests["action.py"]
                assert result["core_version"] == "1.0.2"
                managed_root = (managed_home / "holotree").resolve()
                assert Path(result["python_executable"]).is_relative_to(managed_root)
                assert Path(result["core_origin"]).is_relative_to(managed_root)
                assert Path(result["action_source_path"]).is_relative_to(
                    (data_dir / ".rcc-runtime-sources").resolve()
                )
                evidence.update(
                    {
                        "artifact_digest": descriptor.artifact_digest,
                        "typed_action_result": result,
                        "managed_root": str(managed_root),
                    }
                )
                execution_passed = True
            finally:
                models._global_db = None
    finally:
        cleanup_errors = []
        if pool is not None:
            try:
                pool.dispose()
            except Exception as error:
                cleanup_errors.append(f"Runtime pool cleanup: {type(error).__name__}")
        if provider is not None:
            try:
                provider_harness.terminate_process_tree(provider)
                if provider.poll() is None:
                    cleanup_errors.append("selected RCC provider was not reaped")
            except Exception as error:
                cleanup_errors.append(
                    f"selected RCC provider cleanup: {type(error).__name__}"
                )
        if worker_handle is not None:
            try:
                assert worker_artifact_digest is not None
                evidence["worker"] = _staged_worker_evidence(
                    worker_handle, worker_artifact_digest
                )
            except Exception as error:
                cleanup_errors.append(f"worker lease evidence: {type(error).__name__}")
        evidence["status"] = (
            "PASS" if execution_passed and not cleanup_errors else "FAIL"
        )
        if cleanup_errors:
            evidence["cleanup_errors"] = cleanup_errors
        receipt_path = os.environ.get("ACTIONS_RUNTIME_STAGED_CONSUMER_RECEIPT")
        if receipt_path:
            path = Path(receipt_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )
    assert evidence["status"] == "PASS"


def test_staging_fixture_admission_reuses_approved_tuple_and_rejects_wrong_bytes(
    tmp_path, monkeypatch
):
    from actions.server import _rcc_runtime_adapter as adapter

    rcc = tmp_path / "rcc"
    rcc.write_bytes(b"synthetic exact fixture")
    rcc.chmod(0o700)
    monkeypatch.setenv(
        "ACTIONS_RUNTIME_RCC_TEST_COMPATIBILITY", "released-18.19.5-linux-amd64"
    )
    monkeypatch.setattr(adapter, "_rcc_platform", lambda: "linux-amd64", raising=False)
    monkeypatch.setattr(
        adapter,
        "_binary_sha256",
        lambda _path: "1a617ad7c736fa67c605e20e5ebe3c7d54b02cd548f733e05c809cf49a48db1e",
        raising=False,
    )
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args[0], 0, "v18.19.5\n", ""
        ),
    )
    version, sha = _verify_selected_rcc_fixture(rcc)
    assert version == "v18.19.5"
    assert sha == "1a617ad7c736fa67c605e20e5ebe3c7d54b02cd548f733e05c809cf49a48db1e"
    monkeypatch.setattr(adapter, "_binary_sha256", lambda _path: "0" * 64)
    with pytest.raises(adapter.RccRuntimeError, match="compatibility"):
        _verify_selected_rcc_fixture(rcc)


def test_staging_fixture_default_keeps_exact_pinned_release_bytes(
    tmp_path, monkeypatch
):
    monkeypatch.delenv("ACTIONS_RUNTIME_RCC_TEST_COMPATIBILITY", raising=False)
    rcc = tmp_path / "rcc"
    rcc.write_bytes(b"wrong bytes but version string matches")
    rcc.chmod(0o700)
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args[0], 0, "v18.19.3\n", ""
        ),
    )
    with pytest.raises(AssertionError):
        _verify_selected_rcc_fixture(rcc)


@pytest.mark.parametrize("version", ["v18.19.3", "v18.19.5", "v18.19.6"])
def test_real_staging_descriptor_assertion_binds_measured_version(version):
    import ast
    import inspect
    import textwrap
    from types import SimpleNamespace

    source = ast.parse(
        textwrap.dedent(
            inspect.getsource(test_staged_package_executes_in_managed_rcc_runtime)
        )
    )
    assertions = [
        node
        for node in ast.walk(source)
        if isinstance(node, ast.Assert)
        and any(
            isinstance(child, ast.Attribute) and child.attr == "rcc_version"
            for child in ast.walk(node)
        )
    ]
    assert len(assertions) == 1
    assertion = compile(
        ast.fix_missing_locations(ast.Module(body=assertions, type_ignores=[])),
        "actual-staging-version-assertion",
        "exec",
    )
    exec(
        assertion,
        {"descriptor": SimpleNamespace(rcc_version=version), "rcc_version": version},
    )
    with pytest.raises(AssertionError):
        exec(
            assertion,
            {
                "descriptor": SimpleNamespace(rcc_version="wrong"),
                "rcc_version": version,
            },
        )


@pytest.fixture
def staged_worker_receipt_control(tmp_path):
    from types import SimpleNamespace

    from actions.server._rcc_runtime_adapter import RccProcessHandle

    digest = "sha256:" + "a" * 64
    receipt = tmp_path / "actual-worker.json"
    receipt.write_text(
        json.dumps(
            {
                "artifactDigest": digest,
                "verification": {"valid": True},
                "leaseId": "measured-lease",
                "status": "killed",
            }
        )
    )
    wrapper = RccProcessHandle(SimpleNamespace(), receipt)
    handle = SimpleNamespace(_rcc_wrapper=wrapper, _retirement_result=None)
    return handle, receipt, digest


def test_staged_worker_evidence_retains_raw_lease_and_unknown_cleanup(
    staged_worker_receipt_control,
):
    import hashlib

    handle, path, digest = staged_worker_receipt_control
    evidence = _staged_worker_evidence(handle, digest)
    assert evidence["runtime_receipt"] == json.loads(path.read_text())
    assert (
        evidence["runtime_receipt_sha256"]
        == hashlib.sha256(path.read_bytes()).hexdigest()
    )
    assert evidence["retirement_result"] is None
    assert evidence["wrapper_cleanup_result"] is None
    assert evidence["runtime_receipt"]["status"] == "killed"


@pytest.mark.parametrize(
    "mutation",
    [
        "artifact",
        "verification",
        "lease",
        "wrapper-type",
        "cleanup-type",
        "retirement-type",
    ],
)
def test_staged_worker_evidence_rejects_missing_lease_identity_or_wrong_typed_result(
    staged_worker_receipt_control, mutation
):
    from actions.server._rcc_runtime_adapter import RccRuntimeError

    handle, path, digest = staged_worker_receipt_control
    payload = json.loads(path.read_text())
    if mutation == "artifact":
        payload["artifactDigest"] = "sha256:" + "b" * 64
    elif mutation == "verification":
        payload["verification"]["valid"] = False
    elif mutation == "lease":
        payload.pop("leaseId")
    elif mutation == "wrapper-type":
        handle._rcc_wrapper = {}
    elif mutation == "cleanup-type":
        handle._rcc_wrapper.last_cleanup_result = {"wrapper_reaped": True}
    else:
        handle._retirement_result = {"state": "execution_stopped"}
    path.write_text(json.dumps(payload))
    with pytest.raises(RccRuntimeError):
        _staged_worker_evidence(handle, digest)


def test_staged_worker_evidence_preserves_actual_pending_zombie_and_error_fields(
    staged_worker_receipt_control,
):
    from dataclasses import asdict

    from actions.server._actions_process_pool import WorkerRetirementResult
    from actions.server._common.process import ProcessTreeCleanupResult

    handle, path, digest = staged_worker_receipt_control
    cleanup = ProcessTreeCleanupResult(
        False, (12,), (13,), ("retained-private-error",), False
    )
    retirement = WorkerRetirementResult(
        "pending", False, "retained-private-reason", cleanup
    )
    handle._rcc_wrapper.last_cleanup_result = cleanup
    handle._retirement_result = retirement
    evidence = _staged_worker_evidence(handle, digest)
    assert evidence["wrapper_cleanup_result"] == asdict(cleanup)
    assert evidence["retirement_result"] == asdict(retirement)
    assert evidence["runtime_receipt"] == json.loads(path.read_text())


def _prepare_owned_rcc_test_package_cache(tmp_path, rcc_version, rcc_sha256, *, managed_home=None):
    value=json.loads(os.environ["ACTIONS_RUNTIME_RCC_TEST_PACKAGE_CACHE_CONFIG"])
    cache=Path(value["state_root"])/"actions-home"/"pkgs"
    if managed_home is None:
        cache.mkdir(mode=0o700,exist_ok=True)
    else:
        (managed_home/"pkgs").symlink_to(cache,target_is_directory=True)
    return {"label":value["label"],"shared_only":"pkgs","cold_first_publication":managed_home is None}


@pytest.fixture
def owned_rcc_package_cache_control(monkeypatch):
    """Own only a tiny synthetic Linux task namespace; never run RCC."""
    import tempfile

    if sys.platform != "linux":
        pytest.skip("owned /dev/shm package-cache controls require Linux")
    with tempfile.TemporaryDirectory(
        prefix="actions-rcc-compatibility-actual-control3-unit-", dir="/dev/shm"
    ) as directory:
        root = Path(directory)
        root.chmod(0o700)
        client = root / "actions-home"
        client.mkdir(mode=0o700)
        case = root / "pytest" / "synthetic-stage"
        case.mkdir(parents=True, mode=0o700)
        managed = case / "managed-home"
        managed.mkdir(mode=0o700)
        value = {
            "schema": 1, "runtime_source_sha": "b" * 40,
            "runtime_source_tree": "c" * 40, "label": "control3",
            "binary_sha256": "7e588c01751ca2ae15ba13ef67f2f4b7567697a5a8389737059a73936f509428",
            "state_root": str(root), "package_cache_root": str(client / "pkgs"),
        }
        def configure():
            marker = root / "rcc-package-cache-owner.json"
            raw = json.dumps({key: item for key, item in value.items() if key != "state_marker_sha256"}, sort_keys=True).encode()
            marker.write_bytes(raw)
            marker.chmod(0o600)
            value["state_marker_sha256"] = hashlib.sha256(raw).hexdigest()
            monkeypatch.setenv("ACTIONS_RUNTIME_RCC_TEST_PACKAGE_CACHE_CONFIG", json.dumps(value))
        configure()
        for key, item in {
            "RCC_ROLLBACK_CANDIDATE_SHA": "b" * 40,
            "RCC_ROLLBACK_CANDIDATE_TREE": "c" * 40,
            "ACTIONS_HOME": str(client), "ROBOCORP_HOME": str(client),
            "ACTIONS_RUNTIME_PUBLISHED_DETAILS_RECEIPT": str(root / "publication.json"),
        }.items():
            monkeypatch.setenv(key, item)
        publication = {"schema_version": 1, "status": "PASS",
                       "source": {"commit": "b" * 40, "tree": "c" * 40},
                       "rcc": {"version": "v18.19.3", "sha256": value["binary_sha256"]},
                       "publication": {"invocation_count": 1}}
        def published():
            cache = client / "pkgs"
            cache.mkdir(mode=0o700, exist_ok=True)
            (cache / "synthetic-repodata.json").write_bytes(b"synthetic-package-index")
            receipt = root / "publication.json"
            receipt.write_text(json.dumps(publication))
            receipt.chmod(0o600)
        yield root, case, managed, value, configure, publication, published


def test_owned_rcc_package_cache_preserves_cold_first_and_shared_download_only(
    owned_rcc_package_cache_control,
):
    root, case, managed, value, configure, publication, published = owned_rcc_package_cache_control
    result = _prepare_owned_rcc_test_package_cache(case, "v18.19.3", value["binary_sha256"])
    assert result == {"label": "control3", "shared_only": "pkgs", "cold_first_publication": True}
    assert not any((root / "actions-home" / "pkgs").iterdir())
    published()
    _prepare_owned_rcc_test_package_cache(case, "v18.19.3", value["binary_sha256"], managed_home=managed)
    shared = root / "actions-home" / "pkgs"
    assert (managed / "pkgs").is_symlink() and (managed / "pkgs").resolve() == shared
    assert (managed / "pkgs" / "synthetic-repodata.json").stat().st_ino == (shared / "synthetic-repodata.json").stat().st_ino
    assert not any((managed / name).exists() for name in ("holotree", "artifacts", "provider"))
    assert (shared / "synthetic-repodata.json").read_bytes() == b"synthetic-package-index"


@pytest.mark.parametrize("poison", [
    "unknown_key", "schema_bool", "wrong_binary", "wrong_measured_version",
    "cross_version", "source", "tree", "marker_hash", "marker_mode",
    "marker_symlink", "root_mode", "client_symlink", "target_mode",
    "target_symlink", "target_escape", "case_escape", "managed_symlink",
    "existing_mount", "publication_status", "publication_source",
    "publication_binary", "publication_count", "publication_bool_count",
    "publication_missing", "publication_mode", "publication_symlink",
    "client_env", "empty_cache", "duplicate_config",
])
def test_owned_rcc_package_cache_rejects_poison_before_mount(
    owned_rcc_package_cache_control, monkeypatch, poison,
):
    root, case, managed, value, configure, publication, published = owned_rcc_package_cache_control
    published()
    cache = root / "actions-home" / "pkgs"
    version = "v18.19.3"
    digest = value["binary_sha256"]
    if poison == "unknown_key": value["unknown"] = True
    elif poison == "schema_bool": value["schema"] = True
    elif poison == "wrong_binary": value["binary_sha256"] = "d" * 64
    elif poison == "wrong_measured_version": version = "v18.19.5"
    elif poison == "cross_version": value["label"] = "released5"
    elif poison == "source": value["runtime_source_sha"] = "a" * 40
    elif poison == "tree": value["runtime_source_tree"] = "a" * 40
    elif poison == "target_escape": value["package_cache_root"] = str(root / "other-cache")
    elif poison == "case_escape": case = root / "not-a-pytest-case";case.mkdir(mode=0o700)
    elif poison == "publication_status": publication["status"] = "FAIL"
    elif poison == "publication_source": publication["source"]["commit"] = "a" * 40
    elif poison == "publication_binary": publication["rcc"]["sha256"] = "d" * 64
    elif poison == "publication_count": publication["publication"]["invocation_count"] = 2
    elif poison == "publication_bool_count": publication["publication"]["invocation_count"] = True
    configure()
    receipt = root / "publication.json"
    receipt.write_text(json.dumps(publication))
    if poison == "marker_hash": value["state_marker_sha256"] = "e" * 64;monkeypatch.setenv("ACTIONS_RUNTIME_RCC_TEST_PACKAGE_CACHE_CONFIG",json.dumps(value))
    elif poison == "marker_mode": (root / "rcc-package-cache-owner.json").chmod(0o644)
    elif poison == "marker_symlink": marker=root / "rcc-package-cache-owner.json";other=root / "owned-other-marker";marker.rename(other);marker.symlink_to(other)
    elif poison == "root_mode": root.chmod(0o755)
    elif poison == "client_symlink": client=root / "actions-home";other=root / "other-client";client.rename(other);client.symlink_to(other, target_is_directory=True)
    elif poison == "target_mode": cache.chmod(0o755)
    elif poison == "target_symlink": other=root / "other-cache";cache.rename(other);cache.symlink_to(other,target_is_directory=True)
    elif poison == "managed_symlink": other=case / "other-home";managed.rename(other);managed.symlink_to(other,target_is_directory=True)
    elif poison == "existing_mount": (managed / "pkgs").symlink_to(cache,target_is_directory=True)
    elif poison == "publication_missing": receipt.unlink()
    elif poison == "publication_mode": receipt.chmod(0o644)
    elif poison == "publication_symlink": other=root / "other-publication";receipt.rename(other);receipt.symlink_to(other)
    elif poison == "client_env": monkeypatch.setenv("ACTIONS_HOME",str(root / "wrong-client"))
    elif poison == "empty_cache": (cache / "synthetic-repodata.json").unlink()
    elif poison == "duplicate_config": monkeypatch.setenv("ACTIONS_RUNTIME_RCC_TEST_PACKAGE_CACHE_CONFIG",json.dumps(value)[:-1]+',"schema":1}')
    preexisting = (managed / "pkgs").is_symlink()
    with pytest.raises((AssertionError, ValueError)):
        _prepare_owned_rcc_test_package_cache(case, version, digest, managed_home=managed)
    assert (managed / "pkgs").is_symlink() is preexisting


def test_owned_rcc_package_cache_rejects_prewarmed_first_publication(owned_rcc_package_cache_control):
    root, case, managed, value, configure, publication, published = owned_rcc_package_cache_control
    published()
    with pytest.raises(AssertionError, match="COLD_FIRST_PUBLICATION"):
        _prepare_owned_rcc_test_package_cache(case, "v18.19.3", value["binary_sha256"])
    assert not (managed / "pkgs").exists()
