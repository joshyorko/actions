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
def _run_staged_package_managed_worker(
    tmp_path: Path, monkeypatch, *, persistent=False
):
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
    if persistent:
        # Alternate action payload only; legacy default bytes remain unchanged.
        text = action_bytes.decode("utf-8")
        text = text.replace("import sys\n", "import sys\nimport os\n_counter = 0\n")
        text = text.replace(
            "    source = Path(__file__).resolve()\n",
            "    global _counter\n    _counter += 1\n    source = Path(__file__).resolve()\n",
        )
        text = text.replace(
            "    return {\n",
            "    return {\n        'counter': str(_counter),\n        'worker_pid': str(os.getpid()),\n",
        )
        action_bytes = text.encode("utf-8")
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
                if persistent:
                    expected_result_fields.update({"counter", "worker_pid"})
                descriptor = load_descriptor(package.env_json)
                assert descriptor is not None
                assert descriptor.rcc_version == rcc_version
                worker_artifact_digest = descriptor.artifact_digest
                evidence["runtime_descriptor"] = descriptor.to_dict()
                assert descriptor.provider_reference == provider_url
                settings = Settings(
                    datadir=data_dir, artifacts_dir=tmp_path / "artifacts"
                )
                settings.reuse_processes = persistent
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
                if not persistent:
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
                else:
                    from dataclasses import asdict

                    from actions.server._rcc_runtime_adapter import (
                        approved_rcc_test_policy,
                    )

                    selector = os.environ.get("ACTIONS_RUNTIME_RCC_TEST_COMPATIBILITY")
                    assert selector is not None
                    expected = approved_rcc_test_policy(selector)
                    assert descriptor.rcc_compatibility == expected
                    worker_handle, result_json, calls = _run_persistent_staged_calls(
                        pool,
                        package,
                        action,
                        run,
                        run_dir,
                        source_digests,
                        (managed_home / "holotree").resolve(),
                        (data_dir / ".rcc-runtime-sources").resolve(),
                        asdict(expected),
                    )
                    evidence["persistent_calls"] = calls
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
                if persistent:
                    measured_worker = evidence["worker"]
                    calls = evidence["persistent_calls"]
                    assert isinstance(measured_worker, dict)
                    assert isinstance(calls, list) and calls
                    assert isinstance(calls[0], dict)
                    assert (
                        measured_worker["runtime_receipt_path"]
                        == calls[0]["receipt_path"]
                    )
                    raw = measured_worker["runtime_receipt"]
                    assert isinstance(raw, dict)
                    assert raw["artifactDigest"] == calls[0]["artifact_digest"]
                    assert isinstance(raw.get("leaseId"), str) and raw["leaseId"]
                    evidence["persistent_lease_identity_sha256"] = hashlib.sha256(
                        raw["leaseId"].encode("utf-8")
                    ).hexdigest()
            except Exception as error:
                cleanup_errors.append(f"worker lease evidence: {type(error).__name__}")
        evidence["status"] = (
            "PASS" if execution_passed and not cleanup_errors else "FAIL"
        )
        if cleanup_errors:
            evidence["cleanup_errors"] = cleanup_errors
        receipt_path = os.environ.get(
            "ACTIONS_RUNTIME_STAGED_PERSISTENT_RECEIPT"
            if persistent
            else "ACTIONS_RUNTIME_STAGED_CONSUMER_RECEIPT"
        )
        if receipt_path:
            path = Path(receipt_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )
    assert evidence["status"] == "PASS"


@pytest.mark.real_rcc
def test_staged_package_executes_in_managed_rcc_runtime(tmp_path: Path, monkeypatch):
    """Consume the exact staged bytes through RCC and verify worker provenance."""
    _run_staged_package_managed_worker(tmp_path, monkeypatch)


@pytest.mark.real_rcc
def test_staged_package_persistent_worker_reuses_one_approved_lease(
    tmp_path: Path, monkeypatch
):
    """Six genuine RCC calls retain the approved worker and env-exec lease."""
    _run_staged_package_managed_worker(tmp_path, monkeypatch, persistent=True)


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


def _validate_persistent_call_series(
    rows,
    *,
    expected_compatibility,
    artifact_digest,
    receipt_path,
    source_hash,
    managed_root,
    source_root,
):
    """Validate measured six-call facts; synthetic controls are never actual proof."""
    import math

    assert isinstance(rows, list) and len(rows) == 6
    keys = {
        "ordinal",
        "counter",
        "worker_pid",
        "worker_created",
        "wrapper_pid",
        "wrapper_created",
        "artifact_digest",
        "compatibility",
        "receipt_path",
        "action_source_sha256",
        "action_source_path",
        "python_executable",
        "core_origin",
        "core_version",
    }
    first = rows[0]
    for index, row in enumerate(rows, 1):
        assert isinstance(row, dict) and set(row) == keys
        assert isinstance(row["ordinal"], int) and not isinstance(row["ordinal"], bool)
        assert row["ordinal"] == index
        assert isinstance(row["counter"], int) and not isinstance(row["counter"], bool)
        assert row["counter"] == index
        for key in ("worker_pid", "wrapper_pid"):
            assert isinstance(row[key], int) and not isinstance(row[key], bool)
            assert 0 < row[key] < 2**63
        for key in ("worker_created", "wrapper_created"):
            assert isinstance(row[key], (int, float)) and not isinstance(row[key], bool)
            assert math.isfinite(row[key]) and row[key] > 0
        for key in ("worker_pid", "worker_created", "wrapper_pid", "wrapper_created"):
            assert row[key] == first[key]
        assert row["artifact_digest"] == artifact_digest
        assert isinstance(row["compatibility"], dict)
        assert row["compatibility"] == expected_compatibility
        assert row["receipt_path"] == receipt_path
        assert row["action_source_sha256"] == source_hash
        assert row["core_version"] == "1.0.2"
        for key, root in (
            ("python_executable", managed_root),
            ("core_origin", managed_root),
            ("action_source_path", source_root),
        ):
            assert isinstance(row[key], str) and Path(row[key]).is_absolute()
            assert Path(row[key]).resolve().is_relative_to(root.resolve())
            assert row[key] == first[key]
    return rows


def _run_persistent_staged_calls(
    pool,
    package,
    action,
    run,
    run_dir,
    source_digests,
    managed_root,
    source_root,
    expected_compatibility,
):
    """Execute six real pool calls; never substitute the native runner or handler."""
    from dataclasses import asdict, replace

    import psutil

    from actions.server._rcc_runtime_adapter import load_descriptor

    rows = []
    last_handle = None
    result_json = None
    expected_artifact = None
    expected_receipt = None
    for ordinal in range(1, 7):
        directory = run_dir / str(ordinal)
        directory.mkdir()
        input_json = directory / "input.json"
        input_json.write_text("{}", encoding="utf-8")
        result_json = directory / "result.json"
        output = directory / "output.txt"
        owned_run = replace(run, id=f"{run.id}-{ordinal}", numbered_id=ordinal)
        with pool.obtain_process_for_action(action) as handle:
            assert (
                handle.run_action(
                    owned_run,
                    package,
                    action,
                    input_json,
                    directory,
                    output,
                    result_json,
                    {},
                    {},
                    True,
                )
                == 0
            )
            result = json.loads(result_json.read_text(encoding="utf-8"))["result"]
            assert isinstance(result, dict)
            assert isinstance(result.get("worker_pid"), str)
            assert result["worker_pid"].isdecimal()
            assert result.get("counter") == str(ordinal)
            worker_pid = int(result["worker_pid"])
            assert worker_pid > 0
            wrapper = psutil.Process(handle.pid)
            worker = psutil.Process(worker_pid)
            worker_created = worker.create_time()
            wrapper_created = wrapper.create_time()
            assert worker_pid == wrapper.pid or any(
                parent.pid == wrapper.pid and parent.create_time() == wrapper_created
                for parent in worker.parents()
            )
            descriptor = load_descriptor(package.env_json)
            assert descriptor is not None
            assert descriptor.rcc_compatibility is not None
            compatibility = asdict(descriptor.rcc_compatibility)
            receipt = str(handle._rcc_wrapper.receipt_file.resolve())
            if expected_artifact is None:
                expected_artifact = descriptor.artifact_digest
                expected_receipt = receipt
            rows.append(
                {
                    "ordinal": ordinal,
                    "counter": int(result["counter"]),
                    "worker_pid": worker_pid,
                    "worker_created": worker_created,
                    "wrapper_pid": wrapper.pid,
                    "wrapper_created": wrapper_created,
                    "artifact_digest": descriptor.artifact_digest,
                    "compatibility": compatibility,
                    "receipt_path": receipt,
                    "action_source_sha256": result.get("action_source_sha256"),
                    "action_source_path": result.get("action_source_path"),
                    "python_executable": result.get("python_executable"),
                    "core_origin": result.get("core_origin"),
                    "core_version": result.get("core_version"),
                }
            )
            last_handle = handle
    _validate_persistent_call_series(
        rows,
        expected_compatibility=expected_compatibility,
        artifact_digest=expected_artifact,
        receipt_path=expected_receipt,
        source_hash=source_digests["action.py"],
        managed_root=managed_root,
        source_root=source_root,
    )
    assert last_handle is not None and result_json is not None
    return last_handle, result_json, rows


@pytest.fixture
def persistent_synthetic_series(tmp_path):
    root = tmp_path / "managed"
    source = tmp_path / "sources"
    root.mkdir()
    source.mkdir()
    expected = {
        "compatibility_id": "c" * 64,
        "version": "v18.19.5",
        "binary_sha256": "b" * 64,
        "source_commit": "d" * 40,
    }
    kwargs = {
        "expected_compatibility": expected,
        "artifact_digest": "sha256:" + "a" * 64,
        "receipt_path": str(tmp_path / "real-lease.json"),
        "source_hash": "e" * 64,
        "managed_root": root,
        "source_root": source,
    }
    rows = [
        {
            "ordinal": i,
            "counter": i,
            "worker_pid": 123,
            "worker_created": 1234.125,
            "wrapper_pid": 100,
            "wrapper_created": 1230.5,
            "artifact_digest": kwargs["artifact_digest"],
            "compatibility": json.loads(json.dumps(expected)),
            "receipt_path": kwargs["receipt_path"],
            "action_source_sha256": kwargs["source_hash"],
            "action_source_path": str(source / "snapshot/action.py"),
            "python_executable": str(root / "python"),
            "core_origin": str(root / "actions/__init__.py"),
            "core_version": "1.0.2",
        }
        for i in range(1, 7)
    ]
    return rows, kwargs


def test_valid_synthetic_series_only(persistent_synthetic_series):
    rows, kwargs = persistent_synthetic_series
    assert _validate_persistent_call_series(rows, **kwargs) == rows


@pytest.mark.parametrize(
    "poison",
    [
        "pid",
        "created",
        "wrapper",
        "wrapper_created",
        "artifact",
        "compatibility",
        "lease",
        "counter",
        "missing",
        "bool",
        "overflow",
        "core",
        "python",
        "source",
        "source_hash",
        "nan",
        "few",
        "extra",
    ],
)
def test_poisoned_synthetic_series_is_refused(persistent_synthetic_series, poison):
    rows, kwargs = persistent_synthetic_series
    if poison == "pid":
        rows[3]["worker_pid"] = 124
    elif poison == "created":
        rows[3]["worker_created"] = 1234.126
    elif poison == "wrapper":
        rows[3]["wrapper_pid"] = 101
    elif poison == "wrapper_created":
        rows[3]["wrapper_created"] = 1230.6
    elif poison == "artifact":
        rows[3]["artifact_digest"] = "sha256:" + "f" * 64
    elif poison == "compatibility":
        rows[3]["compatibility"]["binary_sha256"] = "f" * 64
    elif poison == "lease":
        rows[3]["receipt_path"] += "-other"
    elif poison == "counter":
        rows[3]["counter"] = 3
    elif poison == "missing":
        del rows[3]["worker_created"]
    elif poison == "bool":
        rows[3]["worker_pid"] = True
    elif poison == "overflow":
        rows[3]["worker_pid"] = 2**65
    elif poison == "core":
        rows[3]["core_origin"] = "/unowned/private/core.py"
    elif poison == "python":
        rows[3]["python_executable"] = "/unowned/python"
    elif poison == "source":
        rows[3]["action_source_path"] = "/unowned/action.py"
    elif poison == "source_hash":
        rows[3]["action_source_sha256"] = "f" * 64
    elif poison == "nan":
        rows[3]["worker_created"] = float("nan")
    elif poison == "few":
        rows.pop()
    elif poison == "extra":
        rows[3]["unmeasured_field"] = "synthetic"
    with pytest.raises(AssertionError):
        _validate_persistent_call_series(rows, **kwargs)


def _synthetic_loop_fixture(persistent_synthetic_series, monkeypatch, require_reuse):
    import contextlib
    import dataclasses
    import json
    import types

    import psutil

    from actions.server._rcc_runtime_adapter import (
        RccRuntimeDescriptor,
        approved_rcc_test_policy,
    )

    rows, kwargs = persistent_synthetic_series
    expected = dataclasses.asdict(
        approved_rcc_test_policy("released-18.19.5-linux-amd64")
    )
    descriptor = RccRuntimeDescriptor(
        artifact_digest=kwargs["artifact_digest"],
        rcc_version="v18.19.5",
        rcc_compatibility=approved_rcc_test_policy("released-18.19.5-linux-amd64"),
    )
    package = types.SimpleNamespace(env_json=descriptor.to_json())

    class FakeProcess:
        def __init__(self, pid):
            self.pid = pid

        def create_time(self):
            return 1230.5 if self.pid == 100 else 1234.125

        def parents(self):
            return [FakeProcess(100)]

    monkeypatch.setattr(psutil, "Process", FakeProcess)
    calls = []

    class FakeHandle:
        pid = 100
        _rcc_wrapper = types.SimpleNamespace(receipt_file=Path(kwargs["receipt_path"]))

        def run_action(self, *args):
            if require_reuse:
                assert args[-1] is True, "persistent real delegation omitted reuse flag"
            calls.append(args)
            payload = {
                k: rows[0][k]
                for k in (
                    "action_source_sha256",
                    "action_source_path",
                    "python_executable",
                    "core_origin",
                    "core_version",
                )
            }
            payload.update(counter=str(len(calls)), worker_pid="123")
            args[6].write_text(json.dumps({"result": payload}))
            return 0

    class FakePool:
        @contextlib.contextmanager
        def obtain_process_for_action(self, action):
            yield FakeHandle()

    run_type = dataclasses.make_dataclass(
        "SyntheticRun", [("id", str), ("numbered_id", int)]
    )
    run_dir = kwargs["managed_root"].parent / "runs"
    run_dir.mkdir()
    result = _run_persistent_staged_calls(
        FakePool(),
        package,
        object(),
        run_type("synthetic-owned-run", 1),
        run_dir,
        {"action.py": kwargs["source_hash"]},
        kwargs["managed_root"],
        kwargs["source_root"],
        expected,
    )
    assert len(calls) == 6 and len(result[2]) == 6
    return calls


def test_synthetic_delegate_uses_actual_reuse_flag(
    persistent_synthetic_series, monkeypatch
):
    assert all(
        call[-1] is True
        for call in _synthetic_loop_fixture(
            persistent_synthetic_series, monkeypatch, True
        )
    )


def test_synthetic_delegate_uses_existing_descriptor_dataclass_API(
    persistent_synthetic_series, monkeypatch
):
    assert (
        len(_synthetic_loop_fixture(persistent_synthetic_series, monkeypatch, False))
        == 6
    )
