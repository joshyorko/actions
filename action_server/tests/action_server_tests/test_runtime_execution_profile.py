"""Only explicit local configuration can enable the trusted native RCC path."""

import json

import pytest
from action_server_tests import test_activated_reviewed_execution as fixtures

from actions.server.foundry.runtime_profile import (
    RuntimeDeploymentSelection,
    RuntimeExecutionProfile,
    read_runtime_profile,
)
from actions.server.foundry.sql_authorization import SqlFoundryAuthorization

provider = fixtures.provider
postgresql_database = fixtures.postgresql_database
reviewed = fixtures.reviewed
pytestmark = fixtures.pytestmark
pytest_plugins = ["action_server_tests.foundry_fixtures"]


def profile_for(case):
    return RuntimeExecutionProfile(
        schema_version="actions.runtime-rcc-profile/v1",
        admission="trusted-developer-execution",
        prepared_receipt="/tmp/owned-prepared.json",
        worker_id="e530355c-8c66-4ebc-b86d-2d76c85f7169",
        worker=case.selection.worker,
        policy=case.selection.policy,
        output_provider=case.selection.output_provider,
    )


def test_local_profile_selects_exact_authorized_locked_plan(
    reviewed, foundry_package_store, tmp_path
):
    case = fixtures.setup_activated(reviewed, foundry_package_store)
    profile = profile_for(case)
    file = tmp_path / "profile.json"
    file.write_text(profile.model_dump_json())
    assert read_runtime_profile(str(file)) == profile
    assert read_runtime_profile(None) is None
    selector = RuntimeDeploymentSelection(
        case.outputs.capabilities, SqlFoundryAuthorization(case.db), profile
    )
    selected = selector.select_specification(
        case.actor,
        case.staged.ref.workspace_id,
        case.staged.application_id,
        case.staged.package_revisions,
        case.staged.bindings,
    )
    assert selected == case.selection
    data = json.loads(file.read_text())
    for key, value in (
        ("admission", "automatic"),
        ("prepared_receipt", "relative.json"),
        ("worker_id", "invalid"),
        ("extra", True),
    ):
        changed = dict(data, **{key: value})
        file.write_text(json.dumps(changed))
        with pytest.raises(ValueError):
            read_runtime_profile(str(file))


def test_config_does_not_create_or_restore_profile_grants(
    reviewed, foundry_package_store
):
    from actions.server.foundry.models import FoundryAccessGrant
    from actions.server.foundry.sql_authorization import reference_grant_subject

    case = fixtures.setup_activated(reviewed, foundry_package_store)
    profile = profile_for(case)
    selector = RuntimeDeploymentSelection(
        case.outputs.capabilities, SqlFoundryAuthorization(case.db), profile
    )
    subject = reference_grant_subject(profile.worker)
    with case.db.transaction():
        case.db.execute(
            "DELETE FROM foundry_access_grant WHERE subject_id=?", [subject]
        )
    before = len(case.db.all(FoundryAccessGrant))
    with pytest.raises(PermissionError):
        selector.select_specification(
            case.actor,
            case.staged.ref.workspace_id,
            case.staged.application_id,
            case.staged.package_revisions,
            case.staged.bindings,
        )
    assert len(case.db.all(FoundryAccessGrant)) == before
