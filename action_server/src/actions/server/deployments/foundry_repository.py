"""Transactional Deployment persistence on the schema17 shared Runtime DB."""

from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Callable, Sequence
from contextlib import contextmanager
from typing import Any, Iterator
from uuid import uuid4

from actions.server._database import Database, DBError
from actions.server.foundry.models import (
    FoundryAudit,
    FoundryDeploymentHead,
    FoundryDeploymentRevision,
    FoundryPackageRevision,
    FoundryRequest,
)

from .canonical import canonicalize_json, parse_canonical_json
from .foundry_values import (
    AccessDenied,
    ChangeKind,
    DeploymentExecutionSnapshot,
    DeploymentRevision,
    DeploymentSpecification,
    IdempotencyConflict,
    OperationKind,
    RepositoryCorruption,
    StaleDeploymentRevision,
    StoredDeploymentRevision,
)
from .ids import (
    DeploymentId,
    DeploymentRevisionId,
    DeploymentRevisionRef,
    PackageRevisionRef,
    WorkspaceId,
)

_REVISION_SCHEMA = "actions.deployment-revision/v1"


@contextmanager
def _transaction(db: Database) -> Iterator[None]:
    if db.verbose:
        raise ValueError("Deployment repository rejects raw SQL bind diagnostics")
    with db.transaction():
        try:
            yield
        except DBError:
            raise DBError(
                "Foundry SQL operation failed; bind values redacted"
            ) from None


def _canonical_object(value: Any) -> bytes:
    raw = json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return canonicalize_json(raw)


def canonical_specification(specification: DeploymentSpecification) -> bytes:
    """Serialize unordered Deployment selections in a stable order."""
    value = specification.model_dump(mode="json", by_alias=True)
    value["package_revisions"].sort(
        key=lambda ref: (ref["workspace_id"], ref["package_id"], ref["revision_id"])
    )
    for policy in value["capability_plans"]:
        policy["allowed_plans"].sort(
            key=lambda ref: (
                ref["package_revision"]["workspace_id"],
                ref["package_revision"]["package_id"],
                ref["package_revision"]["revision_id"],
                ref["plan_digest"],
            )
        )
    value["capability_plans"].sort(
        key=lambda policy: (
            policy["capability"]["package_revision"]["workspace_id"],
            policy["capability"]["package_revision"]["package_id"],
            policy["capability"]["package_revision"]["revision_id"],
            policy["capability"]["capability_id"],
        )
    )
    value["bindings"].sort(
        key=lambda binding: (
            binding["requirement"]["package_revision"]["workspace_id"],
            binding["requirement"]["package_revision"]["package_id"],
            binding["requirement"]["package_revision"]["revision_id"],
            binding["requirement"]["requirement_id"],
        )
    )
    return _canonical_object(value)


def _canonical_revision(revision: DeploymentRevision) -> bytes:
    value = revision.model_dump(mode="json", by_alias=True)
    value["specification"] = parse_canonical_json(
        canonical_specification(revision.specification)
    )
    return _canonical_object(value)


def _canonical_snapshots(
    entries: Sequence[DeploymentExecutionSnapshot],
) -> bytes:
    value = {_snapshot_key(entry): entry.model_dump(mode="json") for entry in entries}
    if len(value) != len(entries):
        raise ValueError("duplicate Capability/Runtime Plan execution snapshot")
    return _canonical_object(value)


def _snapshot_key(entry: DeploymentExecutionSnapshot) -> str:
    payload = {
        "capability": entry.capability.model_dump(mode="json"),
        "runtime_plan": entry.runtime_plan.model_dump(mode="json"),
    }
    return "sha256:" + hashlib.sha256(_canonical_object(payload)).hexdigest()


def request_digest(
    workspace_id: WorkspaceId,
    deployment_id: DeploymentId,
    expected_revision: DeploymentRevisionRef | None,
    specification: DeploymentSpecification,
    operation_kind: OperationKind,
    rollback_of: DeploymentRevisionRef | None,
) -> str:
    """Hash complete mutation input, including expected base and selections."""
    payload = {
        "schema": "actions.deployment-request/v1",
        "workspace_id": str(workspace_id.root),
        "deployment_id": str(deployment_id.root),
        "expected_revision": (
            expected_revision.model_dump(mode="json", by_alias=True)
            if expected_revision is not None
            else None
        ),
        "operation_kind": operation_kind,
        "rollback_of": (
            rollback_of.model_dump(mode="json") if rollback_of is not None else None
        ),
        "specification": parse_canonical_json(canonical_specification(specification)),
    }
    return "sha256:" + hashlib.sha256(_canonical_object(payload)).hexdigest()


def _revision_digest(
    workspace_id: WorkspaceId,
    deployment_id: DeploymentId,
    sequence: int,
    previous_revision: DeploymentRevisionRef | None,
    rollback_of: DeploymentRevisionRef | None,
    change_kind: str,
    specification_json: bytes,
) -> DeploymentRevisionId:
    payload = {
        "schema": _REVISION_SCHEMA,
        "workspace_id": str(workspace_id.root),
        "deployment_id": str(deployment_id.root),
        "sequence": sequence,
        "previous_revision": (
            previous_revision.revision_id.root if previous_revision else None
        ),
        "rollback_of": rollback_of.revision_id.root if rollback_of else None,
        "change_kind": change_kind,
        "specification": parse_canonical_json(specification_json),
    }
    return DeploymentRevisionId(
        "sha256:" + hashlib.sha256(_canonical_object(payload)).hexdigest()
    )


class FoundryRepository:
    """Use only schema17 Foundry records in the shared Runtime Database."""

    def __init__(self, db: Database):
        if db.verbose:
            raise ValueError("Deployment repository rejects raw SQL bind diagnostics")
        self._db = db

    def current(
        self, workspace_id: WorkspaceId, deployment_id: DeploymentId
    ) -> StoredDeploymentRevision | None:
        workspace_id = WorkspaceId.model_validate(workspace_id)
        deployment_id = DeploymentId.model_validate(deployment_id)
        with self._db.connect():
            heads = self._select(
                FoundryDeploymentHead,
                "SELECT * FROM foundry_deployment_head "
                "WHERE workspace_id=? AND deployment_id=?",
                [str(workspace_id.root), str(deployment_id.root)],
            )
            if not heads:
                return None
            if len(heads) != 1:
                raise RepositoryCorruption("Deployment has multiple active heads")
            head = heads[0]
            try:
                ref = DeploymentRevisionRef(
                    workspace_id=workspace_id,
                    deployment_id=deployment_id,
                    revision_id=DeploymentRevisionId(head.active_revision_id),
                )
            except (TypeError, ValueError) as exc:
                raise RepositoryCorruption(
                    "active Deployment revision is invalid"
                ) from exc
            stored = self._revision(ref)
            if stored is None:
                raise RepositoryCorruption("active Deployment revision is unavailable")
            return stored

    def get_revision(
        self, ref: DeploymentRevisionRef
    ) -> StoredDeploymentRevision | None:
        ref = DeploymentRevisionRef.model_validate(ref)
        with self._db.connect():
            return self._revision(ref)

    def activate(
        self,
        workspace_id: WorkspaceId,
        deployment_id: DeploymentId,
        expected_revision: DeploymentRevisionRef | None,
        specification: DeploymentSpecification,
        *,
        principal_id: str,
        idempotency_key: str,
        input_digest: str,
        operation_kind: OperationKind,
        preflight: Callable[[], None],
        snapshot_builder: Callable[
            [DeploymentRevision], Sequence[DeploymentExecutionSnapshot]
        ],
        rollback_of: DeploymentRevisionRef | None = None,
    ) -> DeploymentRevision:
        """Persist revision, request, audit and head CAS in one transaction."""
        workspace_id = WorkspaceId.model_validate(workspace_id)
        deployment_id = DeploymentId.model_validate(deployment_id)
        specification = DeploymentSpecification.model_validate(specification)
        self._validate_owner(workspace_id, deployment_id, expected_revision)
        self._validate_owner(workspace_id, deployment_id, rollback_of)
        if not principal_id:
            raise ValueError("trusted principal identity is required")
        specification_json = canonical_specification(specification)
        specification = DeploymentSpecification.model_validate_json(specification_json)

        with self._db.connect():
            with _transaction(self._db):
                self._lock_workspace(workspace_id)
                # Recheck live authorization and every selected Package/reference
                # after taking the common Workspace lock. This also applies to
                # idempotent replay so a receipt never bypasses current grants.
                preflight()
                prior_request = self._prior_request(
                    workspace_id, principal_id, operation_kind, idempotency_key
                )
                if prior_request is not None:
                    if prior_request.request_fingerprint != input_digest:
                        raise IdempotencyConflict(
                            "Deployment idempotency key conflicts with changed input"
                        )
                    return self._request_result(
                        prior_request, workspace_id, deployment_id
                    )

                heads = self._heads(workspace_id, deployment_id)
                if len(heads) > 1:
                    raise RepositoryCorruption("Deployment has multiple active heads")
                head = heads[0] if heads else None
                if operation_kind == "create":
                    if expected_revision is not None or head is not None:
                        raise StaleDeploymentRevision(
                            "Deployment already exists or create has an expected base"
                        )
                    if self._history(workspace_id, deployment_id):
                        raise StaleDeploymentRevision(
                            "activate the existing staged edit explicitly"
                        )
                    previous = None
                    sequence = 1
                else:
                    if expected_revision is None or head is None:
                        raise StaleDeploymentRevision(
                            "Deployment current revision does not match expected base"
                        )
                    if head.active_revision_id != expected_revision.revision_id.root:
                        raise StaleDeploymentRevision(
                            "Deployment current revision does not match expected base"
                        )
                    current = self._revision(expected_revision)
                    if current is None:
                        raise RepositoryCorruption(
                            "active Deployment revision is missing"
                        )
                    history = self._history(workspace_id, deployment_id)
                    previous = history[-1].revision.ref
                    sequence = history[-1].revision.sequence + 1

                if operation_kind == "rollback":
                    if rollback_of is None or self._revision(rollback_of) is None:
                        raise StaleDeploymentRevision("rollback target is unavailable")
                elif rollback_of is not None:
                    raise ValueError("only rollback revisions may name a target")

                change_kind: ChangeKind = (
                    "rollback" if operation_kind == "rollback" else "publish"
                )
                revision_id = _revision_digest(
                    workspace_id,
                    deployment_id,
                    sequence,
                    previous,
                    rollback_of,
                    change_kind,
                    specification_json,
                )
                revision = DeploymentRevision(
                    ref=DeploymentRevisionRef(
                        workspace_id=workspace_id,
                        deployment_id=deployment_id,
                        revision_id=revision_id,
                    ),
                    sequence=sequence,
                    previous_revision=previous,
                    rollback_of=rollback_of,
                    change_kind=change_kind,
                    specification=specification,
                )
                stored = StoredDeploymentRevision(
                    revision=revision,
                    execution_snapshots=tuple(snapshot_builder(revision)),
                )
                self._insert_stored(stored)

                if head is None:
                    head = FoundryDeploymentHead(
                        id=str(uuid4()),
                        workspace_id=str(workspace_id.root),
                        deployment_id=str(deployment_id.root),
                        active_revision_id="",
                        lock_version=0,
                    )
                    self._db.insert(head)
                self._cas_activate(head, expected_revision, revision.ref)

                request = FoundryRequest(
                    id=str(uuid4()),
                    workspace_id=str(workspace_id.root),
                    principal_id=principal_id,
                    operation=operation_kind,
                    idempotency_key=idempotency_key,
                    request_fingerprint=input_digest,
                    result_json=_canonical_revision(revision).decode("utf-8"),
                )
                self._db.insert(request)
                self._append_audit(
                    workspace_id,
                    deployment_id,
                    principal_id,
                    operation_kind,
                    request.id,
                    expected_revision,
                    revision.ref,
                )
                return revision

    def history(
        self, workspace_id: WorkspaceId, deployment_id: DeploymentId
    ) -> tuple[StoredDeploymentRevision, ...]:
        """Read bounded immutable edit history; this never chooses activation."""
        with self._db.connect():
            return self._history(workspace_id, deployment_id)

    def _history(
        self, workspace_id: WorkspaceId, deployment_id: DeploymentId
    ) -> tuple[StoredDeploymentRevision, ...]:
        rows = self._select(
            FoundryDeploymentRevision,
            "SELECT * FROM foundry_deployment_revision WHERE workspace_id=? AND deployment_id=? LIMIT 257",
            [str(workspace_id.root), str(deployment_id.root)],
        )
        if len(rows) > 256:
            raise RepositoryCorruption(
                "Deployment history exceeds the bounded authoring limit"
            )
        result = []
        for row in rows:
            ref = DeploymentRevisionRef(
                workspace_id=workspace_id,
                deployment_id=deployment_id,
                revision_id=DeploymentRevisionId(row.revision_id),
            )
            stored = self._revision(ref)
            if stored is None:
                raise RepositoryCorruption("immutable revision disappeared")
            result.append(stored)
        result.sort(key=lambda stored: stored.revision.sequence)
        for index, stored in enumerate(result):
            previous = result[index - 1].revision.ref if index else None
            if (
                stored.revision.sequence != index + 1
                or stored.revision.previous_revision != previous
            ):
                raise RepositoryCorruption(
                    "Deployment edit lineage is not one immutable sequence"
                )
        return tuple(result)

    def lookup_authoring_request(
        self,
        workspace_id: WorkspaceId,
        principal_id: str,
        operation: str,
        key: str,
        fingerprint: str,
    ) -> DeploymentRevision | None:
        with self._db.connect():
            prior = self._prior_request(workspace_id, principal_id, operation, key)
            if prior is None:
                return None
            if prior.request_fingerprint != fingerprint:
                raise IdempotencyConflict("authoring request input changed")
            try:
                receipt = DeploymentRevision.model_validate_json(prior.result_json)
            except ValueError as exc:
                raise RepositoryCorruption("invalid authoring receipt") from exc
            return self._request_result(prior, workspace_id, receipt.ref.deployment_id)

    def stage(
        self,
        workspace_id: WorkspaceId,
        deployment_id: DeploymentId,
        expected_base: DeploymentRevisionRef | None,
        specification: DeploymentSpecification,
        *,
        principal_id: str,
        operation: str,
        idempotency_key: str,
        input_digest: str,
        preflight: Callable[[], None],
        snapshot_builder: Callable[
            [DeploymentRevision], Sequence[DeploymentExecutionSnapshot]
        ],
    ) -> DeploymentRevision:
        """Stage one immutable edit with CAS/receipt/audit, without activation."""
        if operation not in {"canvas.create", "canvas.apply"}:
            raise ValueError("unknown authoring stage operation")
        with self._db.connect():
            with _transaction(self._db):
                self._lock_workspace(workspace_id)
                preflight()
                prior = self._prior_request(
                    workspace_id, principal_id, operation, idempotency_key
                )
                if prior is not None:
                    if prior.request_fingerprint != input_digest:
                        raise IdempotencyConflict("authoring request input changed")
                    receipt = DeploymentRevision.model_validate_json(prior.result_json)
                    owner = (
                        receipt.ref.deployment_id
                        if operation == "canvas.create"
                        else deployment_id
                    )
                    original = self._request_result(prior, workspace_id, owner)
                    supplied = parse_canonical_json(
                        canonical_specification(specification)
                    )
                    retained = parse_canonical_json(
                        canonical_specification(original.specification)
                    )
                    if operation == "canvas.create":
                        # Concurrent create deliveries allocate different candidate
                        # UUIDs before the SQL lock. Compare all authored input,
                        # excluding only that server-owned allocation.
                        for value in (supplied, retained):
                            if isinstance(value, dict) and isinstance(
                                value.get("canvas_application"), dict
                            ):
                                value["canvas_application"].pop("app_id", None)
                    if (
                        supplied != retained
                        or original.previous_revision != expected_base
                    ):
                        raise IdempotencyConflict(
                            "authoring receipt differs from supplied selection"
                        )
                    return original
                history = self._history(workspace_id, deployment_id)
                latest = history[-1].revision if history else None
                if (latest.ref if latest else None) != expected_base:
                    raise StaleDeploymentRevision("authoring edit base changed")
                if operation == "canvas.create" and history:
                    raise StaleDeploymentRevision("application already exists")
                if operation == "canvas.apply" and not history:
                    raise StaleDeploymentRevision("application is unavailable")
                sequence = latest.sequence + 1 if latest else 1
                specification_json = canonical_specification(specification)
                revision = DeploymentRevision(
                    ref=DeploymentRevisionRef(
                        workspace_id=workspace_id,
                        deployment_id=deployment_id,
                        revision_id=_revision_digest(
                            workspace_id,
                            deployment_id,
                            sequence,
                            expected_base,
                            None,
                            "publish",
                            specification_json,
                        ),
                    ),
                    sequence=sequence,
                    previous_revision=expected_base,
                    rollback_of=None,
                    change_kind="publish",
                    specification=specification,
                )
                stored = StoredDeploymentRevision(
                    revision=revision,
                    execution_snapshots=tuple(snapshot_builder(revision)),
                )
                self._insert_stored(stored)
                request = FoundryRequest(
                    str(uuid4()),
                    str(workspace_id.root),
                    principal_id,
                    operation,
                    idempotency_key,
                    input_digest,
                    _canonical_revision(revision).decode("utf-8"),
                )
                self._db.insert(request)
                self._append_audit(
                    workspace_id,
                    deployment_id,
                    principal_id,
                    operation,
                    request.id,
                    expected_base,
                    revision.ref,
                )
                return revision

    def activate_existing(
        self,
        target: DeploymentRevisionRef,
        expected_active: DeploymentRevisionRef | None,
        *,
        principal_id: str,
        operation: str,
        idempotency_key: str,
        input_digest: str,
        preflight: Callable[[DeploymentRevision], None],
        snapshot_builder: Callable[
            [DeploymentRevision], Sequence[DeploymentExecutionSnapshot]
        ],
    ) -> DeploymentRevision:
        """Activate an exact admitted edit; one head remains the sole pointer."""
        if operation not in {"canvas.release", "canvas.rollback"}:
            raise ValueError("unknown authoring activation operation")
        workspace_id, deployment_id = target.workspace_id, target.deployment_id
        self._validate_owner(workspace_id, deployment_id, expected_active)
        with self._db.connect():
            with _transaction(self._db):
                self._lock_workspace(workspace_id)
                stored = self._revision(target)
                if stored is None:
                    raise StaleDeploymentRevision("activation target is unavailable")
                preflight(stored.revision)
                prior = self._prior_request(
                    workspace_id, principal_id, operation, idempotency_key
                )
                if prior is not None:
                    if prior.request_fingerprint != input_digest:
                        raise IdempotencyConflict("authoring request input changed")
                    original = self._request_result(prior, workspace_id, deployment_id)
                    audits = self._select(
                        FoundryAudit,
                        "SELECT * FROM foundry_audit WHERE foundry_request_id=?",
                        [prior.id],
                    )
                    expected_id = (
                        expected_active.revision_id.root if expected_active else ""
                    )
                    if (
                        original.ref != target
                        or len(audits) != 1
                        or audits[0].from_revision_id != expected_id
                        or audits[0].to_revision_id != target.revision_id.root
                    ):
                        raise IdempotencyConflict(
                            "activation receipt differs from supplied target"
                        )
                    return original
                history = self._history(workspace_id, deployment_id)
                if operation == "canvas.release" and (
                    not history or history[-1].revision.ref != target
                ):
                    raise StaleDeploymentRevision(
                        "release candidate is no longer the latest edit"
                    )
                if _canonical_snapshots(
                    tuple(snapshot_builder(stored.revision))
                ) != _canonical_snapshots(stored.execution_snapshots):
                    raise RepositoryCorruption(
                        "staged execution snapshot no longer matches admission"
                    )
                heads = self._heads(workspace_id, deployment_id)
                if len(heads) > 1:
                    raise RepositoryCorruption("multiple active heads")
                if heads:
                    head = heads[0]
                else:
                    if expected_active is not None:
                        raise StaleDeploymentRevision("active revision changed")
                    head = FoundryDeploymentHead(
                        str(uuid4()),
                        str(workspace_id.root),
                        str(deployment_id.root),
                        "",
                        0,
                    )
                    self._db.insert(head)
                self._cas_activate(head, expected_active, target)
                request = FoundryRequest(
                    str(uuid4()),
                    str(workspace_id.root),
                    principal_id,
                    operation,
                    idempotency_key,
                    input_digest,
                    _canonical_revision(stored.revision).decode("utf-8"),
                )
                self._db.insert(request)
                self._append_audit(
                    workspace_id,
                    deployment_id,
                    principal_id,
                    operation,
                    request.id,
                    expected_active,
                    target,
                )
                return stored.revision

    def was_activated(self, ref: DeploymentRevisionRef) -> bool:
        with self._db.connect():
            rows = self._select(
                FoundryAudit,
                "SELECT * FROM foundry_audit WHERE workspace_id=? AND deployment_id=? AND to_revision_id=? AND operation IN ('create','publish','rollback','canvas.release','canvas.rollback') LIMIT 1",
                [
                    str(ref.workspace_id.root),
                    str(ref.deployment_id.root),
                    ref.revision_id.root,
                ],
            )
            return bool(rows)

    def _insert_stored(self, stored: StoredDeploymentRevision) -> None:
        revision = stored.revision
        anchor = self._package_anchor(revision.specification, corruption=False)
        self._db.insert(
            FoundryDeploymentRevision(
                id=str(uuid4()),
                workspace_id=str(revision.ref.workspace_id.root),
                deployment_id=str(revision.ref.deployment_id.root),
                revision_id=revision.ref.revision_id.root,
                foundry_package_revision_id=anchor.id if anchor else None,
                selection_json=_canonical_revision(revision).decode("utf-8"),
                snapshots_json=_canonical_snapshots(stored.execution_snapshots).decode(
                    "utf-8"
                ),
            )
        )

    def _prior_request(
        self,
        workspace_id: WorkspaceId,
        principal_id: str,
        operation_kind: str,
        idempotency_key: str,
    ) -> FoundryRequest | None:
        rows = self._select(
            FoundryRequest,
            "SELECT * FROM foundry_request WHERE workspace_id=? AND principal_id=? "
            "AND operation=? AND idempotency_key=?",
            [str(workspace_id.root), principal_id, operation_kind, idempotency_key],
        )
        if len(rows) > 1:
            raise RepositoryCorruption("duplicate actor-scoped Foundry request")
        return rows[0] if rows else None

    def _request_result(
        self,
        request: FoundryRequest,
        workspace_id: WorkspaceId,
        deployment_id: DeploymentId,
    ) -> DeploymentRevision:
        raw = request.result_json.encode("utf-8")
        try:
            if canonicalize_json(raw) != raw:
                raise ValueError("request result is not canonical")
            receipt = DeploymentRevision.model_validate_json(raw)
            ref = receipt.ref
            if ref.workspace_id != workspace_id or ref.deployment_id != deployment_id:
                raise ValueError("request result has a different Deployment owner")
            expected_digest = _revision_digest(
                workspace_id,
                deployment_id,
                receipt.sequence,
                receipt.previous_revision,
                receipt.rollback_of,
                receipt.change_kind,
                canonical_specification(receipt.specification),
            )
            if expected_digest != ref.revision_id:
                raise ValueError("request result revision digest mismatches")
        except Exception as exc:
            raise RepositoryCorruption(
                "stored Foundry request result is invalid"
            ) from exc
        stored = self._revision(ref)
        if stored is None:
            raise RepositoryCorruption("idempotent Deployment result is unavailable")
        if stored.revision != receipt:
            raise RepositoryCorruption("idempotent Deployment receipt mismatches row")
        return receipt

    def _heads(
        self, workspace_id: WorkspaceId, deployment_id: DeploymentId
    ) -> list[FoundryDeploymentHead]:
        return self._select(
            FoundryDeploymentHead,
            "SELECT * FROM foundry_deployment_head WHERE workspace_id=? "
            "AND deployment_id=?",
            [str(workspace_id.root), str(deployment_id.root)],
        )

    def _revision(self, ref: DeploymentRevisionRef) -> StoredDeploymentRevision | None:
        rows = self._select(
            FoundryDeploymentRevision,
            "SELECT * FROM foundry_deployment_revision WHERE workspace_id=? "
            "AND deployment_id=? AND revision_id=?",
            [
                str(ref.workspace_id.root),
                str(ref.deployment_id.root),
                ref.revision_id.root,
            ],
        )
        if not rows:
            return None
        if len(rows) != 1:
            raise RepositoryCorruption("duplicate immutable Deployment revision")
        record = rows[0]
        raw_revision = record.selection_json.encode("utf-8")
        raw_snapshots = record.snapshots_json.encode("utf-8")
        try:
            if canonicalize_json(raw_revision) != raw_revision:
                raise ValueError("Deployment selection is not canonical")
            if canonicalize_json(raw_snapshots) != raw_snapshots:
                raise ValueError("Deployment snapshots are not canonical")
            revision = DeploymentRevision.model_validate_json(raw_revision)
            if (
                record.workspace_id != str(ref.workspace_id.root)
                or record.deployment_id != str(ref.deployment_id.root)
                or record.revision_id != ref.revision_id.root
                or revision.ref != ref
            ):
                raise ValueError(
                    "stored Deployment revision owner or identity mismatch"
                )
            expected_digest = _revision_digest(
                ref.workspace_id,
                ref.deployment_id,
                revision.sequence,
                revision.previous_revision,
                revision.rollback_of,
                revision.change_kind,
                canonical_specification(revision.specification),
            )
            if expected_digest != ref.revision_id:
                raise ValueError("stored Deployment revision digest mismatches")
            snapshot_data = parse_canonical_json(raw_snapshots)
            if not isinstance(snapshot_data, dict):
                raise ValueError("stored snapshot map must be an object")
            snapshots_list = []
            for key, value in snapshot_data.items():
                entry = DeploymentExecutionSnapshot.model_validate_json(
                    _canonical_object(value)
                )
                if key != _snapshot_key(entry):
                    raise ValueError("stored execution snapshot key mismatches")
                snapshots_list.append(entry)
            snapshots = tuple(snapshots_list)
            stored = StoredDeploymentRevision(
                revision=revision,
                execution_snapshots=snapshots,
            )
            anchor = self._package_anchor(revision.specification, corruption=True)
            if record.foundry_package_revision_id != (
                anchor.id if anchor is not None else None
            ):
                raise ValueError("stored Package integrity anchor mismatches selection")
            self._require_lineage_revision(revision.previous_revision)
            self._require_lineage_revision(revision.rollback_of)
        except Exception as exc:
            raise RepositoryCorruption("stored Deployment revision is invalid") from exc
        return stored

    def _package_anchor(
        self, specification: DeploymentSpecification, *, corruption: bool
    ) -> FoundryPackageRevision | None:
        package_records: list[tuple[PackageRevisionRef, FoundryPackageRevision]] = []
        for package_ref in specification.package_revisions:
            rows = self._select(
                FoundryPackageRevision,
                "SELECT * FROM foundry_package_revision WHERE workspace_id=? "
                "AND package_id=? AND revision_id=?",
                [
                    str(package_ref.workspace_id.root),
                    str(package_ref.package_id.root),
                    package_ref.revision_id.root,
                ],
            )
            if len(rows) != 1:
                if corruption:
                    raise RepositoryCorruption(
                        "stored Deployment references a missing or duplicate Package"
                    )
                raise AccessDenied("Package Revision unavailable or not authorized")
            package_records.append((package_ref, rows[0]))
        package_records.sort(
            key=lambda pair: (
                str(pair[0].workspace_id.root),
                str(pair[0].package_id.root),
                pair[0].revision_id.root,
            )
        )
        return package_records[0][1] if package_records else None

    def _require_lineage_revision(self, ref: DeploymentRevisionRef | None) -> None:
        if ref is None:
            return
        rows = self._select(
            FoundryDeploymentRevision,
            "SELECT * FROM foundry_deployment_revision WHERE workspace_id=? "
            "AND deployment_id=? AND revision_id=?",
            [
                str(ref.workspace_id.root),
                str(ref.deployment_id.root),
                ref.revision_id.root,
            ],
        )
        if len(rows) != 1:
            raise ValueError("Deployment revision lineage target is unavailable")

    def _lock_workspace(self, workspace_id: WorkspaceId) -> None:
        rows = self._execute_returning(
            "UPDATE workspace SET lock_version=lock_version WHERE id=? AND state='active' "
            "RETURNING id",
            [str(workspace_id.root)],
        )
        if len(rows) != 1:
            raise StaleDeploymentRevision("Workspace is unavailable")

    def _cas_activate(
        self,
        head: FoundryDeploymentHead,
        expected_revision: DeploymentRevisionRef | None,
        new_revision: DeploymentRevisionRef,
    ) -> None:
        expected_revision_id = (
            expected_revision.revision_id.root if expected_revision is not None else ""
        )
        if head.active_revision_id != expected_revision_id:
            raise StaleDeploymentRevision(
                "Deployment current revision does not match expected base"
            )
        rows = self._execute_returning(
            "UPDATE foundry_deployment_head SET active_revision_id=?, "
            "lock_version=lock_version+1 WHERE id=? AND workspace_id=? AND deployment_id=? "
            "AND active_revision_id=? AND lock_version=? RETURNING id",
            [
                new_revision.revision_id.root,
                head.id,
                head.workspace_id,
                head.deployment_id,
                expected_revision_id,
                head.lock_version,
            ],
        )
        if len(rows) != 1:
            raise StaleDeploymentRevision(
                "Deployment current revision does not match expected base"
            )

    def _append_audit(
        self,
        workspace_id: WorkspaceId,
        deployment_id: DeploymentId,
        principal_id: str,
        operation_kind: str,
        request_id: str,
        previous: DeploymentRevisionRef | None,
        current: DeploymentRevisionRef,
    ) -> None:
        self._db.insert(
            FoundryAudit(
                id=str(uuid4()),
                workspace_id=str(workspace_id.root),
                deployment_id=str(deployment_id.root),
                principal_id=principal_id,
                operation=operation_kind,
                foundry_request_id=request_id,
                from_revision_id=previous.revision_id.root if previous else "",
                to_revision_id=current.revision_id.root,
                created_ms=str(time.time_ns() // 1_000_000),
            )
        )

    def _select(self, cls: type, sql: str, values: list[Any]) -> list[Any]:
        with self._db.cursor() as cursor:
            self._db.execute_query(cursor, sql, values)
            return [cls(*row) for row in cursor.fetchall()]

    def _execute_returning(self, sql: str, values: list[Any]) -> list[Any]:
        with self._db.cursor() as cursor:
            self._db.execute_update_returning(cursor, sql, values)
            return cursor.fetchall()

    @staticmethod
    def _validate_owner(
        workspace_id: WorkspaceId,
        deployment_id: DeploymentId,
        ref: DeploymentRevisionRef | None,
    ) -> None:
        if ref is not None and (
            ref.workspace_id != workspace_id or ref.deployment_id != deployment_id
        ):
            raise ValueError("Deployment revision is outside the requested owner")
