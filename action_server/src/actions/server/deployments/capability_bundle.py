"""Closed multi-capability carrier of independently verified compiler preimages.

Integrity verification is not compiler issuance or registry admission. This new
format deliberately has no legacy-reader fallback and supplies no execution or
Robot adapter. The shared archive is stored separately from bounded JSON bytes.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from actions.server.deployments import ids
from actions.server.deployments import package_revision_compiler as legacy

BUNDLE_VERSION = "actions.capability-bundle/v1-draft"
MAX_CAPABILITIES = 8
MAX_BUNDLE_METADATA_BYTES = 512 * 1024
_PAYLOAD_FIELDS = (
    "manifest_json",
    "runtime_plan_payload",
    "adapter_specification_payload",
    "input_schema_payload",
    "output_schema_payload",
)
_TEXT_FIELDS = (
    "source_inventory_digest",
    "source_artifact_digest",
    "rcc_specification_digest",
    "rcc_artifact_digest",
)
_HEADER_FIELDS = (
    "runtime_kind",
    "plan_schema_version",
    "contract_id",
    "adapter_version_range",
    "required_features",
    "compatibility_identity_digest",
)


@dataclass(frozen=True)
class CompiledCapabilityBundle:
    manifest_json: bytes
    source_archive: bytes

    @property
    def package_revision_id(self) -> ids.PackageRevisionId:
        return ids.PackageRevisionId(
            legacy._canonical_digest([BUNDLE_VERSION, json.loads(self.manifest_json)])
        )


@dataclass(frozen=True)
class VerifiedCapabilitySelection:
    """One verified selection; its member revision is NOT the bundle revision."""

    package_revision_id: ids.PackageRevisionId
    capability_id: str
    compiled: legacy.CompiledPackageRevision


def _member_record(member: legacy.CompiledPackageRevision) -> dict[str, Any]:
    header = member.runtime_plan_header
    return {
        **{name: json.loads(getattr(member, name)) for name in _PAYLOAD_FIELDS},
        **{name: getattr(member, name) for name in _TEXT_FIELDS},
        "package_revision_id": member.package_revision_id.root,
        "runtime_plan_header": {
            **{name: getattr(header, name) for name in _HEADER_FIELDS},
            "required_features": list(header.required_features),
            "plan_digest": header.plan_digest.root,
        },
    }


def _member_from_record(value: Any, archive: bytes) -> legacy.CompiledPackageRevision:
    if not isinstance(value, dict) or set(value) != set(
        _PAYLOAD_FIELDS + _TEXT_FIELDS + ("package_revision_id", "runtime_plan_header")
    ):
        raise ValueError("unsupported capability preimage shape")
    header = value["runtime_plan_header"]
    if not isinstance(header, dict) or set(header) != set(
        _HEADER_FIELDS + ("plan_digest",)
    ):
        raise ValueError("unsupported adapter header shape")
    if any(not isinstance(value[name], str) for name in _TEXT_FIELDS) or any(
        not isinstance(value[name], dict) for name in _PAYLOAD_FIELDS
    ):
        raise ValueError("invalid capability preimage types")
    if (
        not isinstance(header["plan_schema_version"], int)
        or isinstance(header["plan_schema_version"], bool)
        or any(
            not isinstance(header[name], str)
            for name in _HEADER_FIELDS
            if name not in ("plan_schema_version", "required_features")
        )
    ):
        raise ValueError("invalid adapter header types")
    if not isinstance(header["required_features"], list) or any(
        not isinstance(v, str) for v in header["required_features"]
    ):
        raise ValueError("invalid adapter features")
    return legacy.CompiledPackageRevision(
        manifest_json=legacy._canonical_json(value["manifest_json"]),
        runtime_plan_payload=legacy._canonical_json(value["runtime_plan_payload"]),
        adapter_specification_payload=legacy._canonical_json(
            value["adapter_specification_payload"]
        ),
        input_schema_payload=legacy._canonical_json(value["input_schema_payload"]),
        output_schema_payload=legacy._canonical_json(value["output_schema_payload"]),
        source_inventory_digest=value["source_inventory_digest"],
        source_artifact_digest=value["source_artifact_digest"],
        rcc_specification_digest=value["rcc_specification_digest"],
        rcc_artifact_digest=value["rcc_artifact_digest"],
        source_archive=archive,
        package_revision_id=ids.PackageRevisionId(value["package_revision_id"]),
        runtime_plan_header=legacy.RuntimePlanHeader(
            **{
                name: header[name]
                for name in _HEADER_FIELDS
                if name != "required_features"
            },
            required_features=tuple(header["required_features"]),
            plan_digest=ids.PlanDigest(header["plan_digest"]),
        ),
    )


def _identity(member: legacy.CompiledPackageRevision) -> tuple[str, dict[str, Any]]:
    manifest = json.loads(member.manifest_json)
    capability = manifest["capabilities"][0]
    if (
        capability["kind"] != "action"
        or member.runtime_plan_header.runtime_kind != "rcc"
    ):
        raise ValueError("this bundle compiler only implements Python Action/RCC")
    identity = dict(manifest["identity"])
    identity.pop("revisionDigest")
    return capability["id"], {
        "identity": identity,
        "compatibility": manifest["compatibility"],
    }


def assemble_bundle(
    members: tuple[legacy.CompiledPackageRevision, ...],
) -> CompiledCapabilityBundle:
    """Compose verified immutable preimages; does not establish build issuance."""
    if not isinstance(members, tuple) or not 1 <= len(members) <= MAX_CAPABILITIES:
        raise ValueError("bundle capability count is outside its bound")
    for member in members:
        legacy.verify_compiled_package_revision(member)
    ordered = sorted(members, key=lambda member: _identity(member)[0])
    result = CompiledCapabilityBundle(
        legacy._canonical_json(
            {
                "schemaVersion": BUNDLE_VERSION,
                "sourceArtifactDigest": ordered[0].source_artifact_digest,
                "sourceInventoryDigest": ordered[0].source_inventory_digest,
                "members": [_member_record(member) for member in ordered],
            }
        ),
        ordered[0].source_archive,
    )
    # Do not silently substitute the first archive for another member's bytes.
    if any(member.source_archive != result.source_archive for member in ordered):
        raise ValueError("all capabilities must share one exact source snapshot")
    verify_bundle(result)
    return result


def verify_bundle(
    bundle: CompiledCapabilityBundle,
) -> tuple[legacy.CompiledPackageRevision, ...]:
    """Recompute every preimage and exact membership; never import source."""
    try:
        if (
            not isinstance(bundle, CompiledCapabilityBundle)
            or not isinstance(bundle.source_archive, bytes)
            or len(bundle.source_archive)
            > legacy.MAX_COMPILER_SOURCE_TOTAL_BYTES + 64 * 1024
        ):
            raise ValueError("invalid bounded bundle source")
        value = legacy._canonical_object(
            bundle.manifest_json, MAX_BUNDLE_METADATA_BYTES
        )
        if (
            set(value)
            != {
                "schemaVersion",
                "sourceArtifactDigest",
                "sourceInventoryDigest",
                "members",
            }
            or value["schemaVersion"] != BUNDLE_VERSION
        ):
            raise ValueError("unsupported bundle format")
        if (
            not isinstance(value["members"], list)
            or not 1 <= len(value["members"]) <= MAX_CAPABILITIES
        ):
            raise ValueError("invalid capability count")
        members = tuple(
            _member_from_record(record, bundle.source_archive)
            for record in value["members"]
        )
        names: list[str] = []
        common = None
        plans: set[str] = set()
        build = (members[0].rcc_specification_digest, members[0].rcc_artifact_digest)
        for member in members:
            legacy.verify_compiled_package_revision(member)
            name, identity = _identity(member)
            if common is None:
                common = identity
            if (
                identity != common
                or member.source_inventory_digest != value["sourceInventoryDigest"]
                or member.source_artifact_digest != value["sourceArtifactDigest"]
            ):
                raise ValueError("mixed package scope, compatibility or source")
            if (member.rcc_specification_digest, member.rcc_artifact_digest) != build:
                raise ValueError(
                    "one source environment must have one verified build identity"
                )
            names.append(name)
            digest = member.runtime_plan_header.plan_digest.root
            if digest in plans:
                raise ValueError("duplicate or ambiguously shared plan")
            plans.add(digest)
        if names != sorted(set(names)):
            raise ValueError("capability membership must be unique and ordered")
        # Canonical bytes also reject duplicate JSON members and noncanonical encodings.
        if legacy._canonical_json(value) != bundle.manifest_json:
            raise ValueError("noncanonical bundle metadata")
        return members
    except (KeyError, TypeError, AttributeError, UnicodeError, RecursionError) as exc:
        raise ValueError("malformed capability bundle") from exc


def encode_bundle(bundle: CompiledCapabilityBundle) -> bytes:
    verify_bundle(bundle)
    return bundle.manifest_json


def decode_bundle(payload: bytes, source_archive: bytes) -> CompiledCapabilityBundle:
    bundle = CompiledCapabilityBundle(payload, source_archive)
    verify_bundle(bundle)
    return bundle


def select_capability(
    bundle: CompiledCapabilityBundle,
    revision: ids.PackageRevisionId,
    capability_id: str,
    plan: ids.PlanDigest,
) -> VerifiedCapabilitySelection:
    members = verify_bundle(bundle)
    if revision != bundle.package_revision_id:
        raise ValueError("exact bundle revision required")
    for member in members:
        name, _ = _identity(member)
        if name == capability_id and member.runtime_plan_header.plan_digest == plan:
            return VerifiedCapabilitySelection(revision, name, member)
    raise ValueError("capability and plan are not an exact bundle member")
