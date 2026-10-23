"""Transactional Deployment persistence on the shared Runtime Database.

This repository consumes the integration-owned Deployment tables. It does not
open a second database or install migrations. Its SQL contract is intentionally
small and is listed in ``SHARED_DDL_CONTRACT`` for the integrator.
"""

from __future__ import annotations

import hashlib
import json
from contextlib import contextmanager
from typing import Any, Iterator

from actions.server._database import DBError, Database

from .canonical import canonicalize_json, parse_canonical_json
from .foundry_values import (
    ChangeKind,
    DeploymentRevision,
    DeploymentSpecification,
    IdempotencyConflict,
    OperationKind,
    RepositoryCorruption,
    StaleDeploymentRevision,
)
from .ids import (
    DeploymentId,
    DeploymentRevisionId,
    DeploymentRevisionRef,
    WorkspaceId,
)

_REVISION_SCHEMA = "actions.deployment-revision/v1"

# Integration must add specification_json to the proposed revision table and
# deployment_revision_output_provider_ref. The existing composite-reference
# tables remain the authority for relational scope. workspace_id references the
# existing Runtime workspace(id) row created/owned by the common Run service.
SHARED_DDL_CONTRACT = (
    "deployment(workspace_id, deployment_id, current_revision_id, state)",
    "deployment_revision(workspace_id, deployment_id, revision_id, sequence, "
    "previous_revision_id, rollback_of_revision_id, change_kind, specification_json)",
    "deployment_revision_package(workspace_id, deployment_id, revision_id, "
    "package_id, package_revision_id)",
    "deployment_revision_binding(workspace_id, deployment_id, revision_id, "
    "package_id, package_revision_id, binding_requirement_id, provider_profile_id, "
    "provider_profile_revision_id)",
    "deployment_revision_worker_profile_ref(workspace_id, deployment_id, "
    "revision_id, worker_profile_id, worker_profile_revision_id)",
    "deployment_revision_policy_ref(workspace_id, deployment_id, revision_id, "
    "policy_id, policy_revision_id)",
    "deployment_revision_output_provider_ref(workspace_id, deployment_id, "
    "revision_id, provider_profile_id, provider_profile_revision_id)",
    "deployment_revision_request(workspace_id, idempotency_key, deployment_id, "
    "operation_kind, request_digest, parent_revision_id, result_revision_id)",
)


def _private_diagnostics(db: Database) -> None:
    if db.verbose:
        raise ValueError("Deployment repository rejects raw SQL bind diagnostics")


@contextmanager
def _transaction(db: Database) -> Iterator[None]:
    _private_diagnostics(db)
    with db.transaction():
        try:
            yield
        except DBError:
            raise DBError(
                "Deployment SQL operation failed; bind values redacted"
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
    """Serialize unordered Deployment sets in a stable order."""
    value = specification.model_dump(mode="json")
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


def request_digest(
    workspace_id: WorkspaceId,
    deployment_id: DeploymentId,
    expected_revision: DeploymentRevisionRef | None,
    specification: DeploymentSpecification,
    operation_kind: OperationKind,
    rollback_of: DeploymentRevisionRef | None,
) -> str:
    """Hash the complete request, including expected base and all input refs."""
    payload = {
        "schema": "actions.deployment-request/v1",
        "workspace_id": str(workspace_id.root),
        "deployment_id": str(deployment_id.root),
        "expected_revision": (
            expected_revision.model_dump(mode="json")
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
    change_kind: ChangeKind,
    specification_json: bytes,
) -> DeploymentRevisionId:
    payload = {
        "schema": _REVISION_SCHEMA,
        "workspace_id": str(workspace_id.root),
        "deployment_id": str(deployment_id.root),
        "sequence": sequence,
        "previous_revision": (
            previous_revision.revision_id.root
            if previous_revision is not None
            else None
        ),
        "rollback_of": rollback_of.revision_id.root if rollback_of else None,
        "change_kind": change_kind,
        "specification": parse_canonical_json(specification_json),
    }
    return DeploymentRevisionId(
        "sha256:" + hashlib.sha256(_canonical_object(payload)).hexdigest()
    )


class FoundryRepository:
    """Persist immutable Deployment revisions and CAS the shared active pointer."""

    def __init__(self, db: Database):
        _private_diagnostics(db)
        self._db = db

    def current(
        self, workspace_id: WorkspaceId, deployment_id: DeploymentId
    ) -> DeploymentRevision | None:
        _private_diagnostics(self._db)
        with self._db.connect():
            row = self._one(
                "SELECT current_revision_id FROM deployment "
                "WHERE workspace_id=? AND deployment_id=?",
                [str(workspace_id.root), str(deployment_id.root)],
            )
            if row is None or row[0] is None:
                return None
            ref = DeploymentRevisionRef(
                workspace_id=workspace_id,
                deployment_id=deployment_id,
                revision_id=DeploymentRevisionId(row[0]),
            )
            revision = self._revision(ref)
            if revision is None:
                raise RepositoryCorruption(
                    "active Deployment revision pointer is unavailable"
                )
            return revision

    def get_revision(self, ref: DeploymentRevisionRef) -> DeploymentRevision | None:
        _private_diagnostics(self._db)
        with self._db.connect():
            return self._revision(ref)

    def activate(
        self,
        workspace_id: WorkspaceId,
        deployment_id: DeploymentId,
        expected_revision: DeploymentRevisionRef | None,
        specification: DeploymentSpecification,
        *,
        idempotency_key: str,
        input_digest: str,
        operation_kind: OperationKind,
        rollback_of: DeploymentRevisionRef | None = None,
    ) -> DeploymentRevision:
        """Insert one immutable revision and move the current pointer atomically."""
        _private_diagnostics(self._db)
        self._validate_owner(workspace_id, deployment_id, expected_revision)
        if rollback_of is not None:
            self._validate_owner(workspace_id, deployment_id, rollback_of)
        specification_json = canonical_specification(specification)
        specification = DeploymentSpecification.model_validate_json(specification_json)

        with self._db.connect():
            with _transaction(self._db):
                self._lock_workspace(workspace_id)
                prior_request = self._one(
                    "SELECT deployment_id, operation_kind, request_digest, "
                    "parent_revision_id, result_revision_id "
                    "FROM deployment_revision_request "
                    "WHERE workspace_id=? AND idempotency_key=?",
                    [str(workspace_id.root), idempotency_key],
                )
                if prior_request is not None:
                    if (
                        prior_request[0] != str(deployment_id.root)
                        or prior_request[1] != operation_kind
                        or prior_request[2] != input_digest
                        or prior_request[3]
                        != (
                            expected_revision.revision_id.root
                            if expected_revision is not None
                            else None
                        )
                    ):
                        raise IdempotencyConflict(
                            "Deployment idempotency key conflicts with changed input"
                        )
                    replay_ref = DeploymentRevisionRef(
                        workspace_id=workspace_id,
                        deployment_id=deployment_id,
                        revision_id=DeploymentRevisionId(prior_request[4]),
                    )
                    replay = self._revision(replay_ref)
                    if replay is None:
                        raise RepositoryCorruption(
                            "idempotent Deployment result is unavailable"
                        )
                    return replay

                owner = self._one(
                    "SELECT current_revision_id FROM deployment "
                    "WHERE workspace_id=? AND deployment_id=?",
                    [str(workspace_id.root), str(deployment_id.root)],
                )
                if owner is None:
                    if expected_revision is not None or operation_kind != "create":
                        raise StaleDeploymentRevision(
                            "Deployment current revision does not match expected base"
                        )
                    self._db.execute(
                        "INSERT INTO deployment "
                        "(workspace_id, deployment_id, current_revision_id, state) "
                        "VALUES (?, ?, NULL, 'active')",
                        [str(workspace_id.root), str(deployment_id.root)],
                    )
                    current_revision_id = None
                else:
                    if operation_kind == "create":
                        raise StaleDeploymentRevision("Deployment already exists")
                    current_revision_id = owner[0]

                expected_id = (
                    expected_revision.revision_id.root
                    if expected_revision is not None
                    else None
                )
                if current_revision_id != expected_id:
                    raise StaleDeploymentRevision(
                        "Deployment current revision does not match expected base"
                    )
                if operation_kind == "create" and expected_revision is not None:
                    raise StaleDeploymentRevision(
                        "initial Deployment revision cannot have a parent"
                    )
                if operation_kind != "create" and expected_revision is None:
                    raise StaleDeploymentRevision(
                        "updated Deployment revision requires an expected parent"
                    )
                if operation_kind == "rollback":
                    if rollback_of is None or self._revision(rollback_of) is None:
                        raise StaleDeploymentRevision("rollback target is unavailable")
                elif rollback_of is not None:
                    raise ValueError("only rollback revisions may name a target")

                max_row = self._one(
                    "SELECT COALESCE(MAX(sequence), 0) FROM deployment_revision "
                    "WHERE workspace_id=? AND deployment_id=?",
                    [str(workspace_id.root), str(deployment_id.root)],
                )
                if max_row is None:
                    raise RepositoryCorruption("Deployment sequence is unavailable")
                sequence = int(max_row[0]) + 1
                previous = expected_revision
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
                ref = DeploymentRevisionRef(
                    workspace_id=workspace_id,
                    deployment_id=deployment_id,
                    revision_id=revision_id,
                )
                revision = DeploymentRevision(
                    ref=ref,
                    sequence=sequence,
                    previous_revision=previous,
                    rollback_of=rollback_of,
                    change_kind=change_kind,
                    specification=specification,
                )
                self._insert_revision(revision, specification_json)
                self._cas_activate(
                    workspace_id, deployment_id, expected_id, revision_id
                )
                self._db.execute(
                    "INSERT INTO deployment_revision_request "
                    "(workspace_id, idempotency_key, deployment_id, operation_kind, "
                    "request_digest, parent_revision_id, result_revision_id) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    [
                        str(workspace_id.root),
                        idempotency_key,
                        str(deployment_id.root),
                        operation_kind,
                        input_digest,
                        expected_id,
                        revision_id.root,
                    ],
                )
                return revision

    def _validate_owner(
        self,
        workspace_id: WorkspaceId,
        deployment_id: DeploymentId,
        ref: DeploymentRevisionRef | None,
    ) -> None:
        if ref is not None and (
            ref.workspace_id != workspace_id or ref.deployment_id != deployment_id
        ):
            raise ValueError("Deployment revision is outside the requested owner")

    def _lock_workspace(self, workspace_id: WorkspaceId) -> None:
        rows = self._execute_returning(
            "UPDATE workspace SET lock_version=lock_version "
            "WHERE id=? AND state='active' RETURNING id",
            [str(workspace_id.root)],
        )
        if len(rows) != 1:
            raise StaleDeploymentRevision("Workspace is unavailable")

    def _cas_activate(
        self,
        workspace_id: WorkspaceId,
        deployment_id: DeploymentId,
        expected_revision_id: str | None,
        new_revision_id: DeploymentRevisionId,
    ) -> None:
        sql = (
            "UPDATE deployment SET current_revision_id=? "
            "WHERE workspace_id=? AND deployment_id=? AND current_revision_id IS NULL "
            "RETURNING deployment_id"
        )
        values = [
            new_revision_id.root,
            str(workspace_id.root),
            str(deployment_id.root),
        ]
        if expected_revision_id is not None:
            sql = (
                "UPDATE deployment SET current_revision_id=? "
                "WHERE workspace_id=? AND deployment_id=? AND current_revision_id=? "
                "RETURNING deployment_id"
            )
            values.append(expected_revision_id)
        if len(self._execute_returning(sql, values)) != 1:
            raise StaleDeploymentRevision(
                "Deployment current revision does not match expected base"
            )

    def _insert_revision(
        self, revision: DeploymentRevision, specification_json: bytes
    ) -> None:
        ref = revision.ref
        workspace = str(ref.workspace_id.root)
        deployment = str(ref.deployment_id.root)
        self._db.execute(
            "INSERT INTO deployment_revision "
            "(workspace_id, deployment_id, revision_id, sequence, "
            "previous_revision_id, rollback_of_revision_id, change_kind, "
            "specification_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [
                workspace,
                deployment,
                ref.revision_id.root,
                revision.sequence,
                revision.previous_revision.revision_id.root
                if revision.previous_revision
                else None,
                revision.rollback_of.revision_id.root if revision.rollback_of else None,
                revision.change_kind,
                specification_json.decode("utf-8"),
            ],
        )
        for package in revision.specification.package_revisions:
            self._db.execute(
                "INSERT INTO deployment_revision_package "
                "(workspace_id, deployment_id, revision_id, package_id, "
                "package_revision_id) VALUES (?, ?, ?, ?, ?)",
                [
                    workspace,
                    deployment,
                    ref.revision_id.root,
                    str(package.package_id.root),
                    package.revision_id.root,
                ],
            )
        for binding in revision.specification.bindings:
            requirement = binding.requirement
            self._db.execute(
                "INSERT INTO deployment_revision_binding "
                "(workspace_id, deployment_id, revision_id, package_id, "
                "package_revision_id, binding_requirement_id, provider_profile_id, "
                "provider_profile_revision_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    workspace,
                    deployment,
                    ref.revision_id.root,
                    str(requirement.package_revision.package_id.root),
                    requirement.package_revision.revision_id.root,
                    requirement.requirement_id.root,
                    str(binding.provider.provider_profile_id.root),
                    binding.provider.revision_id.root,
                ],
            )
        worker = revision.specification.worker
        self._db.execute(
            "INSERT INTO deployment_revision_worker_profile_ref "
            "(workspace_id, deployment_id, revision_id, worker_profile_id, "
            "worker_profile_revision_id) VALUES (?, ?, ?, ?, ?)",
            [
                workspace,
                deployment,
                ref.revision_id.root,
                str(worker.worker_profile_id.root),
                worker.revision_id.root,
            ],
        )
        policy = revision.specification.policy
        self._db.execute(
            "INSERT INTO deployment_revision_policy_ref "
            "(workspace_id, deployment_id, revision_id, policy_id, "
            "policy_revision_id) VALUES (?, ?, ?, ?, ?)",
            [
                workspace,
                deployment,
                ref.revision_id.root,
                str(policy.policy_id.root),
                policy.revision_id.root,
            ],
        )
        output_provider = revision.specification.output_provider
        self._db.execute(
            "INSERT INTO deployment_revision_output_provider_ref "
            "(workspace_id, deployment_id, revision_id, provider_profile_id, "
            "provider_profile_revision_id) VALUES (?, ?, ?, ?, ?)",
            [
                workspace,
                deployment,
                ref.revision_id.root,
                str(output_provider.provider_profile_id.root),
                output_provider.revision_id.root,
            ],
        )

    def _revision(self, ref: DeploymentRevisionRef) -> DeploymentRevision | None:
        row = self._one(
            "SELECT sequence, previous_revision_id, rollback_of_revision_id, "
            "change_kind, specification_json FROM deployment_revision "
            "WHERE workspace_id=? AND deployment_id=? AND revision_id=?",
            [
                str(ref.workspace_id.root),
                str(ref.deployment_id.root),
                ref.revision_id.root,
            ],
        )
        if row is None:
            return None
        specification_bytes = row[4].encode("utf-8")
        try:
            if canonicalize_json(specification_bytes) != specification_bytes:
                raise ValueError("stored JSON is not canonical")
            specification = DeploymentSpecification.model_validate_json(
                specification_bytes
            )
            previous = (
                DeploymentRevisionRef(
                    workspace_id=ref.workspace_id,
                    deployment_id=ref.deployment_id,
                    revision_id=DeploymentRevisionId(row[1]),
                )
                if row[1]
                else None
            )
            rollback_of = (
                DeploymentRevisionRef(
                    workspace_id=ref.workspace_id,
                    deployment_id=ref.deployment_id,
                    revision_id=DeploymentRevisionId(row[2]),
                )
                if row[2]
                else None
            )
            revision = DeploymentRevision(
                ref=ref,
                sequence=int(row[0]),
                previous_revision=previous,
                rollback_of=rollback_of,
                change_kind=row[3],
                specification=specification,
            )
        except Exception as exc:
            raise RepositoryCorruption("stored Deployment revision is invalid") from exc
        expected = _revision_digest(
            ref.workspace_id,
            ref.deployment_id,
            revision.sequence,
            previous,
            rollback_of,
            revision.change_kind,
            specification_bytes,
        )
        if expected != ref.revision_id:
            raise RepositoryCorruption("stored Deployment revision digest mismatches")
        return revision

    def _one(self, sql: str, values: list[Any]) -> Any | None:
        with self._db.cursor() as cursor:
            self._db.execute_query(cursor, sql, values)
            return cursor.fetchone()

    def _execute_returning(self, sql: str, values: list[Any]) -> list[Any]:
        with self._db.cursor() as cursor:
            self._db.execute_update_returning(cursor, sql, values)
            return cursor.fetchall()
