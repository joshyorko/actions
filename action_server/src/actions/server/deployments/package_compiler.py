"""Private deterministic compiler proposal for one controlled v2 fixture.

This pure boundary consumes a fresh measured inventory, a complete
harness-owned fixture declaration, caller-supplied source bytes and
caller-supplied RCC/action metadata. It does not acquire files, run RCC,
inspect package code, admit a Package Revision, or publish artifacts. Supplied
measurements and metadata are inputs, not proof of trusted acquisition or
executable discovery.
"""

from __future__ import annotations

import hashlib
import io
import json
import re
import stat
import unicodedata
import zipfile
from dataclasses import dataclass
from typing import Any, Literal, TypeVar

from actions.server.deployments import source_manifest, source_read
from actions.server.deployments.canonical import canonicalize_json, parse_canonical_json
from actions.server.deployments.ids import (
    CapabilityId,
    PackageId,
    PackageRevisionId,
    PlanDigest,
)

COMPILER_PROFILE_VERSION = 1
MAX_CONTROLLED_ACTIONS = 1_000
MAX_CONTROLLED_METADATA_BYTES = 1 * 1024 * 1024
MAX_CONTROLLED_SOURCE_BYTES = 64 * 1024 * 1024
MAX_CONTROLLED_ARCHIVE_BYTES = 64 * 1024 * 1024
_SHA256_DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
_RCC_REQUIRED_VERSION = "v18.19.3"
_RCC_ADAPTER_CONTRACT = "rcc-runtime/v1"
_T = TypeVar("_T")


@dataclass(frozen=True)
class DeclaredAction:
    """Harness-owned package-local capability declaration."""

    capability_id: CapabilityId
    source_path: str
    python_name: str


@dataclass(frozen=True)
class SuppliedActionMetadata:
    """Untrusted metadata supplied by a controlled inspection seam."""

    capability_id: CapabilityId
    source_path: str
    python_name: str
    docs: str
    input_schema_json: bytes
    output_schema_json: bytes
    managed_params_schema_json: bytes = b"{}"
    options_json: bytes = b"{}"


@dataclass(frozen=True)
class SuppliedRccIdentity:
    """Caller-supplied RCC identities; neither field proves RCC was invoked."""

    specification_digest: str
    artifact_digest: str | None = None


@dataclass(frozen=True)
class ProposedControlledCompilation:
    """Portable identity bytes for a proposal, without admission or trust claims."""

    source_archive: bytes
    capability_manifest: bytes
    runtime_plans: tuple[bytes, ...]
    source_digest: str
    capability_digest: str
    plan_digests: tuple[PlanDigest, ...]
    revision_preimage: bytes
    revision_digest: PackageRevisionId
    supplied_rcc_artifact_digest: str | None
    inspection_status: Literal["not_run"] = "not_run"


@dataclass(frozen=True)
class _ActionMetadata:
    capability_id: str
    source_path: str
    python_name: str
    docs: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    managed_params_schema: dict[str, Any]
    options: dict[str, Any]
    byte_size: int


def compile_controlled_fixture(
    *,
    package_id: PackageId,
    measured: source_read.MeasuredSelectedFiles,
    declared_paths: tuple[str, ...],
    protected_paths: tuple[str, ...],
    source_entries: tuple[source_manifest.SuppliedSourceEntry, ...],
    declared_actions: tuple[DeclaredAction, ...],
    supplied_actions: tuple[SuppliedActionMetadata, ...],
    rcc: SuppliedRccIdentity,
) -> ProposedControlledCompilation:
    """Compile deterministic bytes for one explicitly declared fixture.

    The fresh measurement inventory must agree with all supplied file bytes
    and the exact complete fixture path set. This does not prove that the
    caller selected every relevant file for an arbitrary package or that the
    measured tree was globally atomic. RCC identities and action metadata are
    explicitly supplied values; inspection remains unproven and is reported as
    not run in this proposal.
    """
    package_id = PackageId.model_validate(package_id)
    if not isinstance(measured, source_read.MeasuredSelectedFiles):
        raise TypeError("measured must be a fresh MeasuredSelectedFiles value")
    if not isinstance(rcc, SuppliedRccIdentity):
        raise TypeError("rcc must be SuppliedRccIdentity input")
    specification_digest = _require_digest(
        rcc.specification_digest, "RCC specification digest"
    )
    artifact_digest = (
        None
        if rcc.artifact_digest is None
        else _require_digest(rcc.artifact_digest, "RCC artifact digest")
    )

    paths = _bounded_tuple(
        declared_paths, "declared paths", source_manifest.MAX_ENTRIES
    )
    protected = _bounded_tuple(
        protected_paths, "protected paths", source_manifest.MAX_ENTRIES
    )
    entries = _bounded_tuple(
        source_entries, "source entries", source_manifest.MAX_ENTRIES
    )
    expected_paths = _validate_declared_paths(paths)
    for path in protected:
        source_manifest._validated_parts(path)
    if len(set(protected)) != len(protected):
        raise ValueError("protected source paths must be unique")
    source_size = 0
    for entry in entries:
        if not isinstance(entry, source_manifest.SuppliedSourceEntry):
            raise TypeError("source entries must use SuppliedSourceEntry values")
        if entry.kind != "file":
            raise ValueError("controlled fixture source entries must be files")
        if isinstance(entry.content, bytes):
            source_size += len(entry.content)
            if source_size > MAX_CONTROLLED_SOURCE_BYTES:
                raise ValueError("controlled source fixture exceeds its byte bound")
    inventory = source_manifest.validate_proposed_inventory(
        entries, protected_input_names=protected
    )
    if tuple(item.path for item in inventory.entries) != expected_paths:
        raise ValueError("supplied source files differ from the complete declaration")
    if sum(item.size for item in inventory.entries) != source_size:
        raise ValueError("controlled source byte count differs from its inventory")
    expected_archive_size = _zip_stored_archive_size(inventory)
    if expected_archive_size > MAX_CONTROLLED_ARCHIVE_BYTES:
        raise ValueError("controlled source archive exceeds its byte bound")
    _validate_measurement(measured, inventory, expected_paths)

    declared = _validate_declared_actions(
        _bounded_tuple(declared_actions, "declared actions", MAX_CONTROLLED_ACTIONS),
        expected_paths,
    )
    supplied = _validate_supplied_actions(
        _bounded_tuple(
            supplied_actions, "supplied action metadata", MAX_CONTROLLED_ACTIONS
        ),
        expected_paths,
    )
    if set(declared) != set(supplied):
        raise ValueError("supplied actions must match every declaration exactly once")
    if not declared:
        raise ValueError("controlled v2 fixture requires at least one action")
    metadata_size = sum(action.byte_size for action in supplied.values())
    if metadata_size > MAX_CONTROLLED_METADATA_BYTES:
        raise ValueError("controlled action metadata exceeds its byte bound")

    source_archive = _make_source_archive(entries, inventory)
    if (
        len(source_archive) != expected_archive_size
        or len(source_archive) > MAX_CONTROLLED_ARCHIVE_BYTES
    ):
        raise RuntimeError("source archive size differs from its fixed ZIP profile")
    source_digest = _sha256(source_archive)
    action_rows = []
    for capability_id in sorted(declared, key=lambda value: value.encode("utf-8")):
        declared_path, declared_name = declared[capability_id]
        metadata = supplied[capability_id]
        if (metadata.source_path, metadata.python_name) != (
            declared_path,
            declared_name,
        ):
            raise ValueError("supplied action does not match its declaration")
        action_rows.append(
            {
                "capability_id": capability_id,
                "entrypoint": {
                    "file": metadata.source_path,
                    "name": metadata.python_name,
                },
                "docs": metadata.docs,
                "input_schema": metadata.input_schema,
                "output_schema": metadata.output_schema,
                "managed_params_schema": metadata.managed_params_schema,
                "options": metadata.options,
            }
        )
    capability_manifest = _canonical_bytes(
        {
            "domain": "actions-controlled-capabilities",
            "version": 1,
            "actions": action_rows,
        }
    )
    capability_digest = _sha256(capability_manifest)

    plan_actions = [
        {
            "capability_id": capability_id,
            "entrypoint": {"file": path, "name": name},
        }
        for capability_id, (path, name) in sorted(
            declared.items(), key=lambda item: item[0].encode("utf-8")
        )
    ]
    runtime_plan = _canonical_bytes(
        {
            "domain": "actions-controlled-rcc-plan",
            "version": 1,
            "runtime_kind": "rcc",
            "adapter_contract": _RCC_ADAPTER_CONTRACT,
            "required_rcc_version": _RCC_REQUIRED_VERSION,
            "specification_digest": specification_digest,
            "capabilities": plan_actions,
        }
    )
    plan_digest = PlanDigest.model_validate(_sha256(runtime_plan))
    revision_preimage = _canonical_bytes(
        {
            "domain": "actions-controlled-package-revision",
            "version": 1,
            "compiler_profile_version": COMPILER_PROFILE_VERSION,
            "package_id": str(package_id.root),
            "source_policy_version": source_manifest.SOURCE_POLICY_VERSION,
            "source_artifact_digest": source_digest,
            "capability_manifest_digest": capability_digest,
            "runtime_plan_digests": [str(plan_digest.root)],
        }
    )
    return ProposedControlledCompilation(
        source_archive=source_archive,
        capability_manifest=capability_manifest,
        runtime_plans=(runtime_plan,),
        source_digest=source_digest,
        capability_digest=capability_digest,
        plan_digests=(plan_digest,),
        revision_preimage=revision_preimage,
        revision_digest=PackageRevisionId.model_validate(_sha256(revision_preimage)),
        supplied_rcc_artifact_digest=artifact_digest,
    )


def _bounded_tuple(values: tuple[_T, ...], label: str, limit: int) -> tuple[_T, ...]:
    if not isinstance(values, tuple):
        raise TypeError(f"{label} must be supplied as an immutable tuple")
    if len(values) > limit:
        raise ValueError(f"{label} exceed the count limit")
    return values


def _validate_declared_paths(paths: tuple[str, ...]) -> tuple[str, ...]:
    for path in paths:
        source_manifest._validated_parts(path)
    if len(set(paths)) != len(paths):
        raise ValueError("declared source paths must be unique")
    return tuple(sorted(paths, key=lambda path: path.encode("utf-8")))


def _validate_measurement(
    measured: source_read.MeasuredSelectedFiles,
    inventory: source_manifest.ProposedInventoryValidation,
    paths: tuple[str, ...],
) -> None:
    if measured.inventory != inventory:
        raise ValueError("fresh source measurement differs from supplied source bytes")
    if measured.root.file_type != stat.S_IFDIR:
        raise ValueError("fresh source measurement root must be a directory")
    files = {item.path: item for item in measured.files}
    if len(files) != len(measured.files) or set(files) != set(paths):
        raise ValueError(
            "fresh measured file set differs from the complete declaration"
        )
    expected = {item.path: item for item in inventory.entries}
    for path, item in files.items():
        manifest_entry = expected[path]
        if (
            item.object.file_type != stat.S_IFREG
            or item.object.links != 1
            or item.object.size != manifest_entry.size
            or manifest_entry.mode != (0o755 if item.object.mode & 0o111 else 0o644)
            or any(parent.file_type != stat.S_IFDIR for parent in item.directories)
        ):
            raise ValueError("fresh source measurement has invalid file facts")


def _validate_declared_actions(
    actions: tuple[DeclaredAction, ...], paths: tuple[str, ...]
) -> dict[str, tuple[str, str]]:
    result: dict[str, tuple[str, str]] = {}
    entrypoints: set[tuple[str, str]] = set()
    for action in actions:
        if not isinstance(action, DeclaredAction):
            raise TypeError("declared actions must use DeclaredAction values")
        capability_id = CapabilityId.model_validate(action.capability_id)
        source_manifest._validated_parts(action.source_path)
        _validate_python_name(action.python_name)
        if action.source_path not in paths:
            raise ValueError("declared action source must be a measured file")
        key = str(capability_id.root)
        entrypoint = (action.source_path, action.python_name)
        if key in result or entrypoint in entrypoints:
            raise ValueError("declared capability IDs and entrypoints must be unique")
        result[key] = entrypoint
        entrypoints.add(entrypoint)
    return result


def _validate_supplied_actions(
    actions: tuple[SuppliedActionMetadata, ...], paths: tuple[str, ...]
) -> dict[str, _ActionMetadata]:
    result: dict[str, _ActionMetadata] = {}
    entrypoints: set[tuple[str, str]] = set()
    total_size = 0
    for action in actions:
        if not isinstance(action, SuppliedActionMetadata):
            raise TypeError("supplied actions must use SuppliedActionMetadata values")
        capability_id = CapabilityId.model_validate(action.capability_id)
        source_manifest._validated_parts(action.source_path)
        _validate_python_name(action.python_name)
        if action.source_path not in paths:
            raise ValueError("supplied action source must be a measured file")
        if (
            not isinstance(action.docs, str)
            or unicodedata.normalize("NFC", action.docs) != action.docs
        ):
            raise ValueError("action docs must be NFC text")
        try:
            docs_size = len(action.docs.encode("utf-8", errors="strict"))
        except UnicodeEncodeError as exc:
            raise ValueError("action docs must be valid Unicode") from exc
        raw_metadata = (
            action.input_schema_json,
            action.output_schema_json,
            action.managed_params_schema_json,
            action.options_json,
        )
        if any(not isinstance(raw, bytes) for raw in raw_metadata):
            raise TypeError("action metadata JSON values must be immutable bytes")
        total_size += docs_size + sum(len(raw) for raw in raw_metadata)
        if total_size > MAX_CONTROLLED_METADATA_BYTES:
            raise ValueError("controlled action metadata exceeds its byte bound")
        input_schema, input_size = _canonical_json_object(
            action.input_schema_json, "input schema"
        )
        output_schema, output_size = _canonical_json_object(
            action.output_schema_json, "output schema"
        )
        managed_schema, managed_size = _canonical_json_object(
            action.managed_params_schema_json, "managed parameter schema"
        )
        options, options_size = _canonical_json_object(action.options_json, "options")
        if set(options) - {"is_consequential"}:
            raise ValueError("controlled action options contain an unsupported field")
        consequential = options.get("is_consequential")
        if consequential is not None and not isinstance(consequential, bool):
            raise ValueError("is_consequential must be a boolean or null")
        key = str(capability_id.root)
        entrypoint = (action.source_path, action.python_name)
        if key in result or entrypoint in entrypoints:
            raise ValueError("supplied capability IDs and entrypoints must be unique")
        result[key] = _ActionMetadata(
            key,
            action.source_path,
            action.python_name,
            action.docs,
            input_schema,
            output_schema,
            managed_schema,
            options,
            docs_size + input_size + output_size + managed_size + options_size,
        )
        entrypoints.add(entrypoint)
    return result


def _canonical_json_object(raw: bytes, label: str) -> tuple[dict[str, Any], int]:
    if not isinstance(raw, bytes):
        raise TypeError(f"{label} must be immutable bytes")
    if len(raw) > MAX_CONTROLLED_METADATA_BYTES:
        raise ValueError(f"{label} exceeds the metadata byte limit")
    canonical = canonicalize_json(raw)
    if raw != canonical:
        raise ValueError(f"{label} must use canonical JSON bytes")
    parsed = parse_canonical_json(raw)
    if not isinstance(parsed, dict):
        raise ValueError(f"{label} must be a JSON object")
    return parsed, len(raw)


def _validate_python_name(value: str) -> None:
    if (
        not isinstance(value, str)
        or not value
        or unicodedata.normalize("NFC", value) != value
        or not value.isidentifier()
    ):
        raise ValueError("action Python name must be a non-empty NFC identifier")
    try:
        value.encode("utf-8", errors="strict")
    except UnicodeEncodeError as exc:
        raise ValueError("action Python name must be valid Unicode") from exc


def _make_source_archive(
    entries: tuple[source_manifest.SuppliedSourceEntry, ...],
    inventory: source_manifest.ProposedInventoryValidation,
) -> bytes:
    contents = {entry.path: entry.content for entry in entries if entry.kind == "file"}
    output = io.BytesIO()
    with zipfile.ZipFile(
        output, "w", compression=zipfile.ZIP_STORED, allowZip64=False
    ) as archive:
        archive.comment = b""
        for item in sorted(
            inventory.entries, key=lambda entry: entry.path.encode("utf-8")
        ):
            content = contents[item.path]
            if content is None:
                raise ValueError("source archive requires supplied file bytes")
            info = zipfile.ZipInfo(item.path, date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.compress_type = zipfile.ZIP_STORED
            info.external_attr = (stat.S_IFREG | item.mode) << 16
            info.extra = b""
            info.comment = b""
            info.file_size = len(content)
            info.compress_size = len(content)
            archive.writestr(info, content, compress_type=zipfile.ZIP_STORED)
    return output.getvalue()


def _zip_stored_archive_size(
    inventory: source_manifest.ProposedInventoryValidation,
) -> int:
    """Preflight the fixed ZIP_STORED envelope without allocating the archive."""
    # EOCD plus each local and central header, filename bytes, and payload.
    size = 22
    for item in inventory.entries:
        name_size = len(item.path.encode("utf-8", errors="strict"))
        size += 30 + 46 + 2 * name_size + item.size
    return size


def _canonical_bytes(value: dict[str, Any]) -> bytes:
    encoded = json.dumps(
        value, ensure_ascii=False, separators=(",", ":"), allow_nan=False
    ).encode("utf-8", errors="strict")
    return canonicalize_json(encoded)


def _require_digest(value: str, label: str) -> str:
    if not isinstance(value, str) or not _SHA256_DIGEST.fullmatch(value):
        raise ValueError(f"{label} must be lowercase sha256: hexadecimal")
    return value


def _sha256(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()
