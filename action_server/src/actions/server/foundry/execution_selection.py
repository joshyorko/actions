"""Exact registry selection for execution and retained receipt verification."""
from __future__ import annotations

from actions.server.deployments.foundry_values import AccessDenied as RegistryDenied
from actions.server.deployments.package_revision_compiler import (
    CompiledPackageRevision,
    verify_compiled_package_revision,
)
from actions.server.run_outputs.service import AccessDenied


def compiled_for_snapshot(registry, snapshot) -> CompiledPackageRevision:
    """Return adapter preimage; callers retain snapshot's outer Package identity.

    This integrity check does not replace live authorization or fenced publication.
    Legacy and bundle registries must both select the exact capability/plan pair.
    """
    try:
        package = snapshot.capability.package_revision
        if snapshot.runtime_plan.package_revision != package:
            raise ValueError("cross-Package Runtime Plan")
        selected = registry.selection_for(snapshot.capability, snapshot.runtime_plan)
        if (
            selected.package_revision != package
            or selected.capability != snapshot.capability
            or selected.runtime_plan != snapshot.runtime_plan
        ):
            raise ValueError("registry selection differs")
        compiled = selected.compiled
        verify_compiled_package_revision(compiled)
        if (
            compiled.runtime_plan_header.plan_digest
            != snapshot.runtime_plan.plan_digest
        ):
            raise ValueError("adapter plan differs")
        return compiled
    except (RegistryDenied, ValueError, TypeError, AttributeError, KeyError):
        raise AccessDenied("Package execution selection unavailable") from None
