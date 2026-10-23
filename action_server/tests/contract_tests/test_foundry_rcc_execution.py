"""Bounded generated Action execution through the existing Run authority."""

from __future__ import annotations

import hashlib
import json
import os
import stat
import sys
import zipfile
from io import BytesIO
from pathlib import Path
from threading import Event
from uuid import uuid4

import pytest
from action_server_tests.test_foundry_deployments import _refs, _runtime_database
from contract_tests.test_package_revision_compiler import (
    _FakeCompilerExecutor,
    _generated_action_entries,
)

from actions.server._models import Run, RunStatus
from actions.server.data_queries.review import InvoiceReviewService
from actions.server.data_queries.service import InvoiceQueryService
from actions.server.deployments.package_revision_compiler import (
    PinnedRccPackageBuildExecutor,
    PreparedRccEnvironment,
    RccBuildIdentity,
    TrustedDeveloperExecutionAdmission,
    load_prepared_rcc_environment,
)
from actions.server.foundry.models import FoundryAccessGrant
from actions.server.foundry.package_registry import FoundryPackageRegistry
from actions.server.foundry.sql_authorization import (
    SqlFoundryAuthorization,
    reference_grant_subject,
)
from actions.server.foundry.rcc_execution import GeneratedRccExecution, _LOG_LIMIT
from actions.server.run_outputs.filesystem import FilesystemOutputProvider
from actions.server.run_outputs.service import (
    FenceRejected,
    RunOutputControlPlane,
    RunOutputService,
)
from actions.server.run_outputs.types import Actor, ExecutionSnapshot, OutputRef
from actions.server.run_outputs.types import CanvasApplicationRef, CanvasResultScope
from actions.work_items._fencing import ClaimRejected

pytest_plugins = ["action_server_tests.foundry_fixtures"]


def _rcc_path() -> Path | None:
    configured = os.environ.get("ACTIONS_PACKAGE_COMPILER_RCC") or os.environ.get(
        "ACTIONS_RUNTIME_RCC_BINARY"
    )
    if configured:
        return Path(configured)
    candidate = (
        Path(__file__).resolve().parents[2] / "src/actions/server/bin/rcc-18.19.3"
    )
    return candidate if candidate.is_file() else None


def _fake_registry(db, package_store, refs, actor):
    from action_server_tests.test_foundry_package_registry import _grant

    _grant(db, refs, actor)
    registry = FoundryPackageRegistry(
        db,
        package_store,
        SqlFoundryAuthorization(db),
        executor=_FakeCompilerExecutor(),
        admission=TrustedDeveloperExecutionAdmission.TRUSTED,
    )
    result = registry.compile_trusted_source(
        _generated_action_entries(),
        logical_package_key="generated-fixture",
        logical_name="Generated fixture",
        trusted_actor=actor,
        workspace_id=refs.workspace,
        application_id=refs.deployment_id,
    )
    assert result.evidence.ready
    return registry, registry.admit_compiled(
        actor, refs.workspace, result.compiled_package
    )


def _admit_run(db, registry, package, actor, output_provider, *, owner_id=None):
    from action_server_tests.run_outputs.test_service import snapshot

    capability = registry.capability_refs(package)[0]
    declaration = registry.get_capability(capability)
    raw = snapshot(str(package.workspace_id.root)).model_dump(mode="json")
    raw.update(
        capability_authority="package-revision",
        capability=capability.model_dump(mode="json"),
        runtime_plan=declaration.runtime_plans[0].model_dump(mode="json"),
        action_id=registry.action_id_for(capability),
        capability_schema_digest=declaration.schema_digest,
    )
    admitted = ExecutionSnapshot.model_validate(raw)
    with db.transaction():
        for ref in (
            admitted.deployment,
            admitted.worker,
            admitted.policy,
            admitted.output_provider,
        ):
            db.insert(
                FoundryAccessGrant(
                    str(uuid4()),
                    str(package.workspace_id.root),
                    actor.principal_id,
                    "reference",
                    reference_grant_subject(ref),
                    '["execute"]',
                )
            )
    control = RunOutputControlPlane(db, capabilities=registry)
    control.register(admitted)
    control.grant(actor, admitted.deployment, {"execute", "read", "cancel"})
    outputs = RunOutputService(
        db, {admitted.provider_key: output_provider}, capabilities=registry
    )
    run = outputs.admit(actor, admitted, {"value": "synthetic"}, "generated-run")
    fence = outputs.claim(run.id, owner_id or str(uuid4()), lease_seconds=30)
    return outputs, run, fence


def _seed_work_items_journal(db, run_id, fence, *, claim=None, launch=None):
    journal = {
        "version": "actions.generated-rcc-dispatch/v1",
        "mode": "work-items",
        "claim": claim
        or {
            "item_id": str(uuid4()),
            "owner_id": fence.owner_id,
            "epoch": 1,
        },
        "fence": fence.model_dump(),
        "launch": launch,
    }
    with db.transaction():
        db.update_by_id(
            Run,
            run_id,
            {"result": json.dumps(journal, sort_keys=True, separators=(",", ":"))},
        )
    return journal


def test_source_snapshot_rejects_traversal(tmp_path):
    archive_bytes = BytesIO()
    with zipfile.ZipFile(archive_bytes, "w", compression=zipfile.ZIP_STORED) as archive:
        info = zipfile.ZipInfo("../escaped.py")
        info.external_attr = (stat.S_IFREG | 0o644) << 16
        archive.writestr(info, b"pass\n")
    destination = tmp_path / "snapshot"
    with pytest.raises(ValueError, match="invalid entry"):
        GeneratedRccExecution._extract_snapshot(archive_bytes.getvalue(), destination)
    assert not (tmp_path / "escaped.py").exists()


@pytest.mark.parametrize("journal_kind", ["missing", "already-launched"])
def test_explicit_work_items_mode_and_launch_replay_block_before_spawn(
    database_location,
    foundry_package_store,
    tmp_path,
    monkeypatch,
    journal_kind,
):
    refs, actor = _refs(), Actor(principal_id=str(uuid4()))
    output_root = tmp_path / "outputs"
    output_root.mkdir()
    output_fd = os.open(output_root, os.O_RDONLY | os.O_DIRECTORY)
    try:
        with _runtime_database(database_location, refs.workspace, ()) as db:
            with FilesystemOutputProvider(output_fd) as output_provider:
                registry, package = _fake_registry(
                    db, foundry_package_store, refs, actor
                )
                outputs, run, fence = _admit_run(
                    db, registry, package, actor, output_provider
                )
                if journal_kind == "already-launched":
                    _seed_work_items_journal(
                        db,
                        run.id,
                        fence,
                        launch={
                            "id": str(uuid4()),
                            "inputDigest": "sha256:" + "0" * 64,
                        },
                    )
                prepared = PreparedRccEnvironment(
                    robocorp_home=tmp_path,
                    package_yaml_digest="sha256:" + "0" * 64,
                    build_identity=RccBuildIdentity(
                        "sha256:" + "a" * 64, "sha256:" + "b" * 64
                    ),
                )
                rcc = Path("/usr/bin/true")
                monkeypatch.setattr(
                    "actions.server.foundry.rcc_execution.verify_rcc_version",
                    lambda _rcc: "v18.19.3",
                )
                monkeypatch.setattr(
                    "actions.server.foundry.rcc_execution.subprocess.Popen",
                    lambda *args, **kwargs: pytest.fail("RCC must not start"),
                )
                executor = GeneratedRccExecution(
                    registry, outputs, prepared, rcc, tmp_path / "execution"
                )
                if journal_kind == "missing":
                    with pytest.raises(FenceRejected, match="Work Items"):
                        executor.execute(actor, fence, cancelled=Event())
                else:
                    with pytest.raises(FenceRejected, match="reconciliation"):
                        executor.execute(actor, fence, cancelled=Event())
    finally:
        os.close(output_fd)


_PREPARED_RECEIPT = os.environ.get("ACTIONS_PACKAGE_COMPILER_PREPARED_RCC_RECEIPT")
_REAL_RCC = _rcc_path()
pytestmark = [
    pytest.mark.skipif(
        sys.platform != "linux",
        reason="private filesystem Package storage is Linux-only",
    ),
]


@pytest.mark.integration_test
@pytest.mark.skipif(
    not _PREPARED_RECEIPT or _REAL_RCC is None,
    reason="exact prepared RCC receipt and pinned executable required",
)
def test_real_generated_action_executes_and_publishes_measured_result(
    database_location, foundry_package_store, tmp_path
):
    refs, actor = _refs(), Actor(principal_id=str(uuid4()))
    prepared = load_prepared_rcc_environment(Path(_PREPARED_RECEIPT))
    output_root = tmp_path / "outputs"
    output_root.mkdir()
    output_fd = os.open(output_root, os.O_RDONLY | os.O_DIRECTORY)
    try:
        with _runtime_database(database_location, refs.workspace, ()) as db:
            with FilesystemOutputProvider(output_fd) as output_provider:
                from action_server_tests.test_foundry_package_registry import _grant

                _grant(db, refs, actor)
                with db.transaction():
                    db.insert(
                        FoundryAccessGrant(
                            str(uuid4()),
                            str(refs.workspace.root),
                            actor.principal_id,
                            "workspace",
                            str(refs.workspace.root),
                            '["read_application"]',
                        )
                    )
                registry = FoundryPackageRegistry(
                    db,
                    foundry_package_store,
                    SqlFoundryAuthorization(db),
                    executor=PinnedRccPackageBuildExecutor(prepared),
                    admission=TrustedDeveloperExecutionAdmission.TRUSTED,
                )
                action_source = (
                    b"from actions import action\n\n"
                    b"@action\n"
                    b"def generated_echo(value: str) -> str:\n"
                    + ("    print('x' * " + str(_LOG_LIMIT + 4096) + ")\n").encode()
                    + b"    return value\n"
                )
                compilation = registry.compile_trusted_source(
                    _generated_action_entries(action_source),
                    logical_package_key="generated-fixture",
                    logical_name="Generated fixture",
                    trusted_actor=actor,
                    workspace_id=refs.workspace,
                    application_id=refs.deployment_id,
                )
                assert compilation.evidence.ready, compilation.evidence
                package = registry.admit_compiled(
                    actor, refs.workspace, compilation.compiled_package
                )
                owner_id = str(uuid4())
                outputs, run, fence = _admit_run(
                    db, registry, package, actor, output_provider, owner_id=owner_id
                )
                admitted_snapshot, _inputs = outputs.execution_context(actor, fence)
                scope = CanvasResultScope(
                    deployment=admitted_snapshot.deployment,
                    application=CanvasApplicationRef(
                        workspace_id=str(refs.workspace.root),
                        app_id=str(uuid4()),
                        revision_id="sha256:" + "c" * 64,
                    ),
                )
                queue = InvoiceReviewService(InvoiceQueryService(outputs, {})).queue(
                    scope
                )
                item_id = queue.seed_input({"synthetic": True}, item_id=str(uuid4()))
                work_item_claim = queue.reserve_fenced(owner_id, lease_seconds=30)
                assert work_item_claim.item_id == item_id
                journal = _seed_work_items_journal(
                    db,
                    run.id,
                    fence,
                    claim={
                        "item_id": work_item_claim.item_id,
                        "owner_id": work_item_claim.owner_id,
                        "epoch": work_item_claim.epoch,
                    },
                )

                executor = GeneratedRccExecution(
                    registry,
                    outputs,
                    prepared,
                    _REAL_RCC,
                    tmp_path / "execution",
                )

                work_item_liveness_transactions = []

                def work_item_liveness() -> bool:
                    work_item_liveness_transactions.append(outputs.db.in_transaction())
                    try:
                        queue.renew_fenced(work_item_claim, lease_seconds=30)
                    except ClaimRejected:
                        return True
                    return False

                completed = executor.execute(actor, fence, cancelled=work_item_liveness)
                assert work_item_liveness_transactions[-1] is True
                with outputs.db.transaction():
                    queue._require(work_item_claim)

                assert completed.status == RunStatus.PASSED
                envelope = json.loads(completed.result)
                receipt = envelope["result"]
                assert receipt["mode"] == "work-items"
                assert receipt["claim"]["owner_id"] == fence.owner_id
                assert receipt["lineage"] == {
                    "packageRevision": admitted_snapshot.capability.package_revision.model_dump(
                        mode="json"
                    ),
                    "runtimePlan": admitted_snapshot.runtime_plan.model_dump(
                        mode="json"
                    ),
                    "workItemClaim": journal["claim"],
                    "runId": run.id,
                    "attemptFence": fence.model_dump(),
                }
                assert (
                    receipt["sourceArtifactDigest"]
                    == compilation.compiled_package.source_artifact_digest
                )
                assert (
                    receipt["rccArtifactDigest"]
                    == prepared.build_identity.artifact_digest
                )
                assert len(envelope["outputs"]) == 4
                output_receipts = {item["name"]: item for item in receipt["outputs"]}
                assert set(output_receipts) == {
                    "generated-action-result.json",
                    "rcc-receipt.json",
                    "rcc-stdout.log",
                    "rcc-stderr.log",
                }
                stdout_receipt = receipt["execution"]["stdout"]
                assert stdout_receipt["retainedBytes"] == _LOG_LIMIT
                assert stdout_receipt["truncated"] is True
                assert stdout_receipt["discardedObservedBytes"] > 0
                for name, item in output_receipts.items():
                    output_ref = OutputRef.model_validate(item["ref"])
                    assert output_ref.model_dump() in envelope["outputs"]
                    with outputs.resolve(
                        actor, str(refs.workspace.root), output_ref.handle
                    ) as resolved:
                        payload = resolved.read()
                    assert len(payload) == item["size"]
                    assert (
                        "sha256:" + hashlib.sha256(payload).hexdigest()
                        == item["digest"]
                    )
                    if name == "rcc-stdout.log":
                        assert len(payload) == _LOG_LIMIT
                    elif name == "rcc-receipt.json":
                        assert json.loads(payload)["status"] == "completed"
                output = OutputRef.model_validate(
                    output_receipts["generated-action-result.json"]["ref"]
                )
                with outputs.resolve(
                    actor, str(refs.workspace.root), output.handle
                ) as resolved:
                    assert json.loads(resolved.read()) == "synthetic"
    finally:
        os.close(output_fd)
