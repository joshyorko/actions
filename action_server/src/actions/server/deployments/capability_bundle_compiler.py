"""Bounded multi-Action compiler using unchanged singleton phase verification.

Each selected Action has its own plan preimage. Shared source/environment does
not imply plan equivalence. Native phases run serially, at most eight times;
this deliberately conservative compiler does not cache execution evidence.
"""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from actions.server.deployments import package_revision_compiler as legacy
from actions.server.deployments.capability_bundle import (
    MAX_CAPABILITIES,
    CompiledCapabilityBundle,
    assemble_bundle,
)
from actions.server.deployments.source_manifest import SuppliedSourceEntry


@dataclass(frozen=True)
class PythonCapabilityPolicy:
    action_name: str
    policy: legacy.PackageCompilationPolicy

    def __post_init__(self) -> None:
        if (
            not isinstance(self.action_name, str)
            or not self.action_name.isascii()
            or not self.action_name.isidentifier()
            or len(self.action_name) > 120
        ):
            raise ValueError("explicit bounded Python Action name required")
        if not isinstance(self.policy, legacy.PackageCompilationPolicy):
            raise ValueError("typed per-capability policy required")


@dataclass(frozen=True)
class BundleCompilationPolicy:
    capabilities: tuple[PythonCapabilityPolicy, ...]

    def __post_init__(self) -> None:
        if (
            not isinstance(self.capabilities, tuple)
            or not 1 <= len(self.capabilities) <= MAX_CAPABILITIES
            or any(
                not isinstance(item, PythonCapabilityPolicy)
                for item in self.capabilities
            )
        ):
            raise ValueError("bounded typed capability policies required")
        names = [item.action_name for item in self.capabilities]
        if len(set(names)) != len(names):
            raise ValueError("duplicate Action policy")
        first = self.capabilities[0].policy
        common = (
            "package_id",
            "logical_name",
            "actions_runtime_range",
            "actions_core_range",
            "compiler_normalization_version",
            "rcc_adapter_version_range",
        )
        if any(
            any(getattr(item.policy, name) != getattr(first, name) for name in common)
            for item in self.capabilities
        ):
            raise ValueError("capabilities must share exact package compatibility")


@dataclass(frozen=True)
class BundleCompilationOutcome:
    bundle: CompiledCapabilityBundle | None
    receipts: tuple[legacy.CompilationReceipt, ...]
    failure_code: str | None


class _SelectingExecutor:
    def __init__(
        self,
        delegate: legacy.PackageBuildExecutor,
        selected: str,
        names: frozenset[str],
        inspection: list[bytes],
    ):
        self.delegate = delegate
        self.selected = selected
        self.names = names
        self.inspection = inspection

    @property
    def rcc_version(self) -> str:
        return self.delegate.rcc_version

    def build_environment(
        self, package_yaml: Path, workspace: Path
    ) -> legacy.RccBuildIdentity:
        return self.delegate.build_environment(package_yaml, workspace)

    def import_action(
        self, build: legacy.RccBuildIdentity, package_dir: Path, workspace: Path
    ) -> dict[str, Any]:
        metadata = self.delegate.import_action(build, package_dir, workspace)
        if not isinstance(metadata, dict):
            raise ValueError("metadata must be an object")
        if metadata.get("actions_spec_version") != "v2":
            raise ValueError("unsupported Action inspection contract")
        actions = metadata.get("actions")
        if not isinstance(actions, list) or len(actions) != len(self.names):
            raise ValueError("all declared Actions must be inspected")
        found: dict[str, dict[str, Any]] = {}
        normalized: dict[str, Any] = {}
        for action in actions:
            name, _module, _input, _output = legacy._validate_action_metadata(
                {"actions": [action]}, package_dir
            )
            if name in found or name not in self.names:
                raise ValueError("duplicate or undeclared Action")
            found[name] = action
            normalized[name] = {"module": _module, "input": _input, "output": _output}
        if found.keys() != self.names:
            raise ValueError("missing declared Action")
        canonical = legacy._canonical_json(normalized)
        if len(canonical) > legacy.MAX_COMPILER_METADATA_BYTES:
            raise ValueError("inspection exceeds bundle metadata bound")
        if self.inspection and self.inspection[0] != canonical:
            raise ValueError("Action inspection changed between compiler phases")
        if not self.inspection:
            self.inspection.append(canonical)
        return {**metadata, "actions": [found[self.selected]]}

    def run_tests(
        self, build: legacy.RccBuildIdentity, package_dir: Path, workspace: Path
    ) -> None:
        self.delegate.run_tests(build, package_dir, workspace)


def compile_generated_python_bundle(
    entries: Iterable[SuppliedSourceEntry],
    policy: BundleCompilationPolicy,
    *,
    protected_input_names: Iterable[str],
    admission: legacy.TrustedDeveloperExecutionAdmission | None,
    executor: legacy.PackageBuildExecutor | None = None,
    execution_root: Path | None = None,
) -> BundleCompilationOutcome:
    if not isinstance(policy, BundleCompilationPolicy):
        raise ValueError(
            "typed Python bundle policy required; Robot compilation unsupported"
        )
    # Bound the input iterator before materializing it, using canonical source policy.
    snapshot = legacy.snapshot_source_entries(
        entries, protected_input_names=protected_input_names
    )
    frozen_entries = tuple(
        SuppliedSourceEntry(item.path, "file", item.content, item.mode)
        for item in snapshot.files
    )
    active = executor or legacy.PinnedRccPackageBuildExecutor()
    members: list[legacy.CompiledPackageRevision] = []
    receipts: list[legacy.CompilationReceipt] = []
    inspection: list[bytes] = []
    names = frozenset(item.action_name for item in policy.capabilities)
    for item in sorted(policy.capabilities, key=lambda item: item.action_name):
        result = legacy.compile_generated_python_action(
            frozen_entries,
            item.policy,
            protected_input_names=(),
            admission=admission,
            executor=_SelectingExecutor(active, item.action_name, names, inspection),
            execution_root=execution_root,
        )
        receipts.append(result.receipt)
        if result.compiled_package is None:
            return BundleCompilationOutcome(
                None, tuple(receipts), result.receipt.failure_code
            )
        members.append(legacy.verify_compilation_outcome(result))
    try:
        bundle = assemble_bundle(tuple(members))
    except ValueError:
        return BundleCompilationOutcome(
            None, tuple(receipts), "bundle_integrity_failed"
        )
    return BundleCompilationOutcome(bundle, tuple(receipts), None)


def verify_bundle_compilation_outcome(
    outcome: BundleCompilationOutcome,
) -> CompiledCapabilityBundle:
    """Verify all phase receipts against exact ordered members; not issuance."""
    from actions.server.deployments.capability_bundle import verify_bundle

    if (
        not isinstance(outcome, BundleCompilationOutcome)
        or outcome.bundle is None
        or outcome.failure_code is not None
    ):
        raise ValueError("successful bundle compilation required")
    members = verify_bundle(outcome.bundle)
    if not isinstance(outcome.receipts, tuple) or len(outcome.receipts) != len(members):
        raise ValueError("one exact compilation receipt per capability required")
    for member, receipt in zip(members, outcome.receipts):
        legacy.verify_compilation_outcome(legacy.CompilationOutcome(member, receipt))
    return outcome.bundle
