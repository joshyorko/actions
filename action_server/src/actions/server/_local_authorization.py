"""Explicit offline local-owner grants over the existing SQLite authority.

The caller must exclude other same-user filesystem mutations. The canonical
Runtime mutex excludes cooperating Runtime writers, not arbitrary SQLite tools.
No startup, activation, discovery or execution path calls this module.
"""
from __future__ import annotations

import hashlib
import json
import os
import stat
from dataclasses import asdict
from pathlib import Path
from typing import Literal
from uuid import NAMESPACE_URL, uuid5

from pydantic import BaseModel, ConfigDict, Field, model_validator

from actions.server._common.app_mutex import obtain_app_mutex
from actions.server._database import Database
from actions.server._models import get_all_model_classes
from actions.server.deployments.foundry_repository import FoundryRepository
from actions.server.deployments.ids import (
    DeploymentRevisionRef,
    WorkspaceId,
    WorkspaceScopedRef,
    require_workspace_scope,
)
from actions.server.foundry.bootstrap import _OWNER_OPERATIONS, _ROOT_REQUEST
from actions.server.foundry.models import (
    FoundryAccessGrant,
    FoundryAudit,
    FoundryRequest,
)
from actions.server.foundry.runtime_profile import (
    RuntimeExecutionProfile,
    read_runtime_profile,
)
from actions.server.foundry.sql_authorization import reference_grant_subject
from actions.server.run_outputs.models import RunAccessGrant, Workspace
from actions.server.run_outputs.service import (
    RunOutputControlPlane,
    _canonical,
    _key,
    _lock_workspace,
    _now,
    _transaction,
    _update,
)
from actions.server.run_outputs.types import Actor, canonical_uuid

RunPermission = Literal["read", "execute", "cancel"]
QueuePermission = Literal[
    "work_items.read",
    "work_items.enqueue",
    "work_items.claim",
    "work_items.complete",
    "work_items.cancel",
    "work_items.review",
    "work_items.artifact.read",
]


class LocalAuthorizationRequest(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")
    schema_version: Literal["actions.local-authorization/v1"]
    operation: Literal[
        "authorize-generated-source", "authorize-exact-deployment", "revoke"
    ]
    target: Literal["generated-source", "deployment"]
    request_id: str = Field(min_length=1, max_length=128)
    workspace_id: WorkspaceId
    runtime_profile: str
    deployment: DeploymentRevisionRef | None = None
    run_permissions: tuple[RunPermission, ...] = Field(
        default=(),
        description="Explicit application-ID Run operations, including retained and future revisions subject to live checks. Revoke subtracts these named operations.",
    )
    queue_permissions: tuple[QueuePermission, ...] = Field(
        default=(),
        description="Exact Deployment-revision permissions cover all its queues and require a Workspace gate. Revoke changes only this command-owned Foundry rows.",
    )
    expected_grants_digest: str | None = Field(
        default=None, pattern=r"^sha256:[a-f0-9]{64}$"
    )

    @model_validator(mode="after")
    def scope(self):
        if self.operation != "revoke" and self.operation != "authorize-" + (
            "generated-source"
            if self.target == "generated-source"
            else "exact-deployment"
        ):
            raise ValueError("operation and explicit target differ")
        if self.target == "generated-source":
            if (
                self.deployment is not None
                or self.run_permissions
                or self.queue_permissions
            ):
                raise ValueError(
                    "source authorization cannot include deployment permissions"
                )
        elif (
            self.deployment is None
            or not self.run_permissions
            and not self.queue_permissions
        ):
            raise ValueError("exact Deployment and named permissions required")
        if len(set(self.run_permissions)) != len(self.run_permissions) or len(
            set(self.queue_permissions)
        ) != len(self.queue_permissions):
            raise ValueError("duplicate permissions")
        return self


def _digest(value) -> str:
    return (
        "sha256:" + hashlib.sha256(_canonical(value, 128 * 1024).encode()).hexdigest()
    )


def _owned(path: Path, *, directory: bool = False) -> Path:
    if not path.is_absolute() or ".." in path.parts:
        raise ValueError("absolute canonical local path required")
    for parent in (path, *path.parents):
        if parent.is_symlink():
            raise ValueError("symlink paths are unsupported")
    info = path.stat()
    if info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise ValueError("private owner-only filesystem permissions required")
    if not (stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode)):
        raise ValueError("existing regular file or directory required")
    if not directory and info.st_nlink != 1:
        raise ValueError("hardlinked state is unsupported")
    return path


def _owner(db: Database) -> tuple[Actor, WorkspaceId]:
    rows = db.all(FoundryRequest, where="id=?", values=[_ROOT_REQUEST])
    if len(rows) != 1:
        raise ValueError("existing Runtime owner bootstrap receipt required")
    row = rows[0]
    expected = (
        "sha256:" + hashlib.sha256(json.dumps(_OWNER_OPERATIONS).encode()).hexdigest()
    )
    if (
        row.operation != "runtime.bootstrap"
        or row.idempotency_key != "runtime-bootstrap/v1"
        or row.request_fingerprint != expected
        or len(row.result_json) > 2048
    ):
        raise ValueError("invalid Runtime owner bootstrap lineage")
    data = json.loads(row.result_json)
    if set(data) != {"principal_id", "workspace_id"} or data != {
        "principal_id": row.principal_id,
        "workspace_id": row.workspace_id,
    }:
        raise ValueError("Runtime owner receipt identity differs")
    canonical_uuid(row.principal_id)
    actor, workspace = (
        Actor(principal_id=row.principal_id),
        WorkspaceId.model_validate(row.workspace_id),
    )
    audits = db.all(FoundryAudit, where="foundry_request_id=?", values=[_ROOT_REQUEST])
    if len(audits) != 1 or (
        audits[0].workspace_id,
        audits[0].principal_id,
        audits[0].operation,
        audits[0].deployment_id,
        audits[0].from_revision_id,
        audits[0].to_revision_id,
    ) != (row.workspace_id, row.principal_id, "runtime.bootstrap", "", "", ""):
        raise ValueError("Runtime owner audit lineage differs")
    if (
        len(
            db.select(
                Workspace,
                "SELECT * FROM workspace WHERE id=? AND state='active'",
                [row.workspace_id],
            )
        )
        != 1
    ):
        raise ValueError("active saved Workspace required")
    return actor, workspace


def _operations(payload: str) -> set[str]:
    if len(payload.encode()) > 2048:
        raise ValueError("bounded grant policy required")
    values = json.loads(payload)
    if (
        not isinstance(values, list)
        or len(values) > 32
        or any(not isinstance(value, str) for value in values)
        or len(values) != len(set(values))
    ):
        raise ValueError("invalid retained grant operations")
    return set(values)


def _grant_id(actor, workspace, target_key, kind, subject):
    return str(
        uuid5(
            NAMESPACE_URL,
            "actions.local-authorization/v1:"
            + _digest(
                [actor.principal_id, str(workspace.root), target_key, kind, subject]
            ),
        )
    )


def apply_local_authorization(
    db: Database,
    request: LocalAuthorizationRequest,
    profile: RuntimeExecutionProfile,
    registry,
    *,
    dry_run: bool,
) -> dict:
    """Trusted CLI seam; caller owns offline mutex and validated local files."""
    with db.connect(), _transaction(db):
        actor, workspace = _owner(db)
        if (
            request.workspace_id != workspace
            or profile.worker.workspace_id != workspace
        ):
            raise ValueError("request/profile outside saved owner Workspace")
        _lock_workspace(db, str(workspace.root))
        refs = (profile.worker, profile.policy, profile.output_provider)
        for profile_ref in refs:
            require_workspace_scope(profile_ref, workspace)
        target_key = "generated-source:" + _digest(
            [ref.model_dump(mode="json") for ref in refs]
        )
        grants: dict[tuple[str, str], set[str]] = {}
        if request.target == "generated-source":
            grants[("workspace", str(workspace.root))] = {"execute_generated_source"}
            for profile_ref in refs:
                grants[("reference", reference_grant_subject(profile_ref))] = {
                    "deploy",
                    "execute",
                }
        else:
            ref = request.deployment
            assert ref is not None
            if ref.workspace_id != workspace:
                raise ValueError("Deployment outside saved Workspace")
            repository = FoundryRepository(db)
            selected = (
                repository.get_revision(ref)
                if request.operation == "revoke"
                else repository.current(workspace, ref.deployment_id)
            )
            if selected is None or selected.revision.ref != ref:
                raise ValueError("exact active immutable Deployment required")
            if request.operation == "revoke" and not repository.was_activated(ref):
                raise ValueError("previously activated retained Deployment required")
            spec = selected.revision.specification
            if (spec.worker, spec.policy, spec.output_provider) != refs:
                raise ValueError("Deployment differs from explicit runtime profile")
            if (
                registry is None and request.operation != "revoke"
            ) or not spec.package_revisions:
                raise ValueError("verified native Package registry required")
            if request.operation != "revoke":
                for package in spec.package_revisions:
                    registry.load_verified(package)
            selected_refs: list[WorkspaceScopedRef] = [
                ref,
                *refs,
                *spec.package_revisions,
            ]
            for policy in spec.capability_plans:
                if (
                    request.operation != "revoke"
                    and registry.get_capability(policy.capability) is None
                ):
                    raise ValueError("undeclared native capability")
                selected_refs.append(policy.capability)
                for plan in policy.allowed_plans:
                    if (
                        request.operation != "revoke"
                        and registry.get_runtime_plan(plan) is None
                    ):
                        raise ValueError("undeclared native runtime plan")
                    selected_refs.append(plan)
            target_key = "deployment:" + reference_grant_subject(ref)
            if "execute" in request.run_permissions:
                grants[("workspace", str(workspace.root))] = {"execute"}
                for selected_ref in selected_refs:
                    grants[("reference", reference_grant_subject(selected_ref))] = {
                        "execute"
                    }
            if request.queue_permissions:
                grants.setdefault(("workspace", str(workspace.root)), set()).update(
                    request.queue_permissions
                )
                grants.setdefault(
                    ("reference", reference_grant_subject(ref)), set()
                ).update(request.queue_permissions)
        owned = {}
        for (kind, subject), operations in grants.items():
            key = _grant_id(actor, workspace, target_key, kind, subject)
            rows = db.all(FoundryAccessGrant, where="id=?", values=[key])
            if rows and (
                rows[0].workspace_id,
                rows[0].principal_id,
                rows[0].subject_kind,
                rows[0].subject_id,
            ) != (str(workspace.root), actor.principal_id, kind, subject):
                raise ValueError("owned grant identity conflict")
            owned[key] = (kind, subject, operations, rows[0] if rows else None)
        if request.operation == "revoke" and any(
            row is not None for _, _, _, row in owned.values()
        ):
            history = db.select(
                FoundryRequest,
                "SELECT r.* FROM foundry_request r JOIN foundry_audit a ON a.foundry_request_id=r.id WHERE r.workspace_id=? AND r.principal_id=? AND r.operation=? AND a.to_revision_id=? LIMIT 129",
                [
                    str(workspace.root),
                    actor.principal_id,
                    "runtime.local-authorization",
                    request.deployment.revision_id.root if request.deployment else "",
                ],
            )
            if len(history) > 128:
                raise ValueError("bounded owned grant provenance required")
            valid = False
            for prior in history:
                if len(prior.result_json) > 16384:
                    continue
                prior_receipt = json.loads(prior.result_json)
                expected_operation = (
                    "authorize-generated-source"
                    if request.target == "generated-source"
                    else "authorize-exact-deployment"
                )
                if (
                    prior_receipt.get("operation") != expected_operation
                    or prior_receipt.get("deployment")
                    != (
                        request.deployment.model_dump(mode="json")
                        if request.deployment
                        else None
                    )
                    or prior_receipt.get("profileReferences")
                    != [ref.model_dump(mode="json") for ref in refs]
                ):
                    continue
                prior_id = _key(
                    "actions.local-authorization/request/v1",
                    str(workspace.root),
                    actor.principal_id,
                    prior.idempotency_key,
                )
                audits = db.all(
                    FoundryAudit, where="foundry_request_id=?", values=[prior.id]
                )
                if (
                    prior.id == prior_id
                    and len(audits) == 1
                    and (
                        audits[0].id,
                        audits[0].workspace_id,
                        audits[0].principal_id,
                        audits[0].operation,
                        audits[0].deployment_id,
                        audits[0].from_revision_id,
                        audits[0].to_revision_id,
                    )
                    == (
                        str(uuid5(NAMESPACE_URL, prior_id)),
                        str(workspace.root),
                        actor.principal_id,
                        "runtime.local-authorization",
                        str(request.deployment.deployment_id.root)
                        if request.deployment
                        else "",
                        request.deployment.revision_id.root
                        if request.deployment
                        else "",
                        request.deployment.revision_id.root
                        if request.deployment
                        else "",
                    )
                ):
                    valid = True
                    break
            if not valid:
                raise ValueError(
                    "command-owned grants require valid authorization audit provenance"
                )
        run_rows = []
        if request.deployment is not None:
            run_key = _key(
                "actions.run-access/v1",
                str(workspace.root),
                str(request.deployment.deployment_id.root),
                actor.principal_id,
            )
            run_rows = db.all(RunAccessGrant, where="id=?", values=[run_key])
            if run_rows and (
                run_rows[0].workspace_id,
                run_rows[0].deployment_id,
                run_rows[0].principal_id,
            ) != (
                str(workspace.root),
                str(request.deployment.deployment_id.root),
                actor.principal_id,
            ):
                raise ValueError("Run grant identity conflict")
        state = _digest(
            {
                "foundry": sorted(
                    (key, asdict(row) if row else None)
                    for key, (_, _, _, row) in owned.items()
                ),
                "run": [asdict(row) for row in run_rows],
            }
        )
        scope = {
            "owner": actor.principal_id,
            "workspace": str(workspace.root),
            "target": request.target,
            "operation": request.operation,
            "deployment": request.deployment.model_dump(mode="json")
            if request.deployment
            else None,
            "profileReferences": [ref.model_dump(mode="json") for ref in refs],
            "foundryScope": "Workspace generated-source execution and exact profile deploy/execute references"
            if request.target == "generated-source"
            else "explicit selected native references plus necessary Workspace gates",
            "runScope": "application ID, including retained/future revisions subject to other live checks"
            if request.deployment
            else None,
            "queueScope": "all queues of exact Deployment revision plus Workspace permission gate"
            if request.queue_permissions
            else None,
            "expected_grants_digest": state,
            "runPermissions": list(request.run_permissions),
            "queuePermissions": list(request.queue_permissions),
            "foundryRows": len(owned),
            "dryRun": dry_run,
        }
        fingerprint = _digest(
            {
                "request": request.model_dump(mode="json"),
                "profile": profile.model_dump(mode="json"),
            }
        )
        request_key = _key(
            "actions.local-authorization/request/v1",
            str(workspace.root),
            actor.principal_id,
            request.request_id,
        )
        previous = db.all(FoundryRequest, where="id=?", values=[request_key])
        if previous:
            previous_request = previous[0]
            audits = db.all(
                FoundryAudit, where="foundry_request_id=?", values=[request_key]
            )
            if (
                previous_request.request_fingerprint != fingerprint
                or previous_request.principal_id != actor.principal_id
                or previous_request.workspace_id != str(workspace.root)
                or previous_request.operation != "runtime.local-authorization"
                or previous_request.idempotency_key != request.request_id
                or len(previous_request.result_json) > 16384
                or len(audits) != 1
                or (
                    audits[0].id,
                    audits[0].workspace_id,
                    audits[0].principal_id,
                    audits[0].operation,
                    audits[0].deployment_id,
                    audits[0].from_revision_id,
                    audits[0].to_revision_id,
                )
                != (
                    str(uuid5(NAMESPACE_URL, request_key)),
                    str(workspace.root),
                    actor.principal_id,
                    "runtime.local-authorization",
                    str(request.deployment.deployment_id.root)
                    if request.deployment
                    else "",
                    request.deployment.revision_id.root if request.deployment else "",
                    request.deployment.revision_id.root if request.deployment else "",
                )
            ):
                raise ValueError("request id conflict or invalid audit")
            return dict(
                scope,
                replay=True,
                historicalReceipt=json.loads(previous_request.result_json),
            )
        if dry_run:
            return scope
        if request.expected_grants_digest != state:
            raise ValueError("grant state changed; obtain current dry-run digest")
        for key, (kind, subject, operations, row) in owned.items():
            current = _operations(row.operations_json) if row else set()
            result = (
                current - operations
                if request.operation == "revoke"
                else current | operations
            )
            if row:
                _update(
                    db,
                    FoundryAccessGrant,
                    key,
                    {"operations_json": _canonical(sorted(result), 2048)},
                )
            elif result:
                db.insert(
                    FoundryAccessGrant(
                        key,
                        str(workspace.root),
                        actor.principal_id,
                        kind,
                        subject,
                        _canonical(sorted(result), 2048),
                    )
                )
        if request.deployment is not None and request.run_permissions:
            current = _operations(run_rows[0].operations_json) if run_rows else set()
            result = (
                current - set(request.run_permissions)
                if request.operation == "revoke"
                else current | set(request.run_permissions)
            )
            control = RunOutputControlPlane(db)
            if result:
                control.grant(actor, request.deployment, result)
            else:
                control.revoke(actor, request.deployment)
        receipt = dict(scope, dryRun=False, replay=False)
        db.insert(
            FoundryRequest(
                request_key,
                str(workspace.root),
                actor.principal_id,
                "runtime.local-authorization",
                request.request_id,
                fingerprint,
                _canonical(receipt, 16384),
            )
        )
        db.insert(
            FoundryAudit(
                str(uuid5(NAMESPACE_URL, request_key)),
                str(workspace.root),
                str(request.deployment.deployment_id.root)
                if request.deployment
                else "",
                actor.principal_id,
                "runtime.local-authorization",
                request_key,
                request.deployment.revision_id.root if request.deployment else "",
                request.deployment.revision_id.root if request.deployment else "",
                str(_now(db)),
            )
        )
        return receipt


class _OfflineCompiler:
    @property
    def rcc_version(self) -> str:
        raise RuntimeError("offline authorization cannot execute RCC")

    def build_environment(self, package_yaml, workspace):
        raise RuntimeError("offline authorization cannot execute RCC")

    def import_action(self, build, package_dir, workspace):
        raise RuntimeError("offline authorization cannot execute RCC")

    def run_tests(self, build, package_dir, workspace) -> None:
        raise RuntimeError("offline authorization cannot execute RCC")


def run_local_authorization(
    datadir: str, request_file: str, *, dry_run: bool = False
) -> dict:
    if os.name != "posix":
        raise ValueError(
            "offline authorization requires POSIX private ownership semantics"
        )
    if os.environ.get("ACTION_SERVER_DATABASE_URL"):
        raise ValueError(
            "offline local SQLite only; external database configuration rejected"
        )
    root = _owned(Path(datadir), directory=True)
    db_path = _owned(root / "server.db")
    request_path = _owned(Path(request_file))
    if request_path.stat().st_size > 16384:
        raise ValueError("bounded authorization request required")
    with request_path.open("rb") as stream:
        raw_request = stream.read(16385)
    if len(raw_request) > 16384:
        raise ValueError("bounded authorization request required")
    request = LocalAuthorizationRequest.model_validate_json(raw_request)
    profile = read_runtime_profile(str(_owned(Path(request.runtime_profile))))
    assert profile is not None
    lock_path = root / "action_server.lock"
    if lock_path.exists() or lock_path.is_symlink():
        lock_info = lock_path.lstat()
        if (
            not stat.S_ISREG(lock_info.st_mode)
            or lock_info.st_uid != os.getuid()
            or lock_info.st_nlink != 1
        ):
            raise ValueError("existing canonical lock must be an owned regular file")
    try:
        mutex = obtain_app_mutex(
            data_dir=root,
            lock_basename="action_server.lock",
            app_name="Action Server offline authorization",
            timeout=0,
            kill_lock_holder=False,
        )
    except RuntimeError as exc:
        raise ValueError("Runtime is running or its lock is unavailable") from exc
    if mutex is None:
        raise ValueError("Runtime is running; stop it before offline authorization")
    provider = None
    try:
        # Recheck after obtaining the canonical Runtime lock; never create/migrate.
        _owned(db_path)
        for suffix in ("-wal", "-shm", "-journal"):
            if (
                Path(str(db_path) + suffix).exists()
                or Path(str(db_path) + suffix).is_symlink()
            ):
                raise ValueError("unsettled SQLite sidecar; cleanly stop Runtime first")
        db = Database(db_path)
        with db.connect():
            db.initialize(get_all_model_classes())
            registry = None
            if request.target == "deployment" and request.operation != "revoke":
                from actions.server.foundry.package_registry import (
                    FoundryPackageRegistry,
                )
                from actions.server.foundry.sql_authorization import (
                    SqlFoundryAuthorization,
                )
                from actions.server.run_outputs.filesystem import (
                    FilesystemOutputProvider,
                )

                blobs = _owned(root / "blobs", directory=True)
                fd = os.open(blobs, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
                try:
                    provider = FilesystemOutputProvider(fd)
                finally:
                    os.close(fd)
                registry = FoundryPackageRegistry(
                    db,
                    provider,
                    SqlFoundryAuthorization(db),
                    executor=_OfflineCompiler(),
                )
            return apply_local_authorization(
                db, request, profile, registry, dry_run=dry_run
            )
    finally:
        if provider is not None:
            provider.close()
        mutex.release_mutex()
