"""Dedicated genuine RCC -> immutable SQL Package proof, not a native job yet."""

import os
from pathlib import Path
from uuid import uuid4

import pytest
from action_server_tests.test_foundry_deployments import _refs, _runtime_database
from action_server_tests.test_foundry_package_registry import (
    _admit_native_run,
    _compile,
    _grant,
)

from actions.server.deployments.package_revision_compiler import (
    PinnedRccPackageBuildExecutor,
    TrustedDeveloperExecutionAdmission,
    load_prepared_rcc_environment,
)
from actions.server.foundry.package_registry import FoundryPackageRegistry
from actions.server.foundry.sql_authorization import SqlFoundryAuthorization
from actions.server.run_outputs.types import Actor

pytest_plugins = ["action_server_tests.foundry_fixtures"]
pytestmark = [
    pytest.mark.integration_test,
    pytest.mark.skipif(
        not os.environ.get("ACTIONS_PACKAGE_COMPILER_PREPARED_RCC_RECEIPT"),
        reason="dedicated exact-manifest pinned RCC cache receipt required",
    ),
]


def test_real_generated_build_import_test_admits_exact_package(
    database_location, foundry_package_store, tmp_path
):
    prepared = load_prepared_rcc_environment(
        Path(os.environ["ACTIONS_PACKAGE_COMPILER_PREPARED_RCC_RECEIPT"])
    )
    refs, actor = _refs(), Actor(principal_id=str(uuid4()))
    with _runtime_database(database_location, refs.workspace, ()) as db:
        _grant(db, refs, actor)
        registry = FoundryPackageRegistry(
            db,
            foundry_package_store,
            SqlFoundryAuthorization(db),
            executor=PinnedRccPackageBuildExecutor(prepared),
            admission=TrustedDeveloperExecutionAdmission.TRUSTED,
            execution_root=tmp_path,
        )
        compiled = _compile(registry, refs, actor)
        ref = registry.admit_compiled(actor, refs.workspace, compiled)
        assert registry.load(ref) == compiled
        assert registry.evidence(ref).ready
        capability = registry.capability_refs(ref)[0]
        assert (
            registry.resolve_capability(actor, refs.workspace, capability) == capability
        )
        _admit_native_run(db, registry, ref, actor)
