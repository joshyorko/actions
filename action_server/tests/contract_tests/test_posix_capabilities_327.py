"""Private extraction refuses missing mode support before creating state."""

import os

import pytest

from actions.server.deployments import package_revision_compiler as compiler
from actions.server.deployments import source_manifest
from actions.server.foundry import rcc_execution


@pytest.mark.parametrize("capability", [None, False])
def test_private_extraction_requires_chmod_before_creating_destination(
    tmp_path, monkeypatch, capability
):
    snapshot = compiler.snapshot_source_entries(
        [source_manifest.SuppliedSourceEntry("action.py", "file", b"pass\n", 0o644)],
        protected_input_names=[],
    )
    archive = compiler._deterministic_source_archive(snapshot)

    class WithoutChmod:
        fchmod = capability

        def __getattr__(self, name):
            return getattr(os, name)

    monkeypatch.setattr(rcc_execution, "os", WithoutChmod())
    destination = tmp_path / "snapshot"
    with pytest.raises(RuntimeError, match="requires fchmod"):
        rcc_execution.GeneratedRccExecution._extract_snapshot(archive, destination)
    assert not destination.exists()
