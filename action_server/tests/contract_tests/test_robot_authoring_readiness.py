from types import SimpleNamespace
from uuid import uuid4

import pytest

from actions.server.deployments.ids import PackageRevisionId, PackageRevisionRef
from actions.server.foundry.authoring_values import AuthoringError, CompilationEvidence
from actions.server.foundry.robot_authoring import RobotAuthoringEvidence
from actions.server.foundry.sql_authoring import SqlAuthoringAuthority


@pytest.mark.parametrize("robot_first", [False, True])
def test_unqualified_robot_cannot_hide_in_multi_package_projection(robot_first):
    robot_id=PackageRevisionId("sha256:"+"1"*64)
    python_id=PackageRevisionId("sha256:"+"2"*64)
    workspace=str(uuid4())
    refs=[PackageRevisionRef(workspace_id=workspace,package_id=str(uuid4()),revision_id=revision) for revision in (robot_id,python_id)]
    if not robot_first:
        refs.reverse()
    robot=RobotAuthoringEvidence(robot_id,"direct")
    python=CompilationEvidence("succeeded","passed","passed","passed",package_revision_id=python_id)
    authority=SqlAuthoringAuthority.__new__(SqlAuthoringAuthority)
    authority.package_evidence=lambda ref: robot if ref.revision_id==robot_id else python
    specification=SimpleNamespace(package_revisions=refs)
    assert authority._compilation(specification) == robot
    with pytest.raises(AuthoringError,match="dry-run"):
        authority._compilation(specification,require_ready=True)


def test_public_reply_robot_fields_never_fabricate_python_pass():
    from actions.server.foundry.authoring import _backend_evidence_result
    robot=RobotAuthoringEvidence(PackageRevisionId("sha256:"+"1"*64),"direct")
    result=_backend_evidence_result(robot)
    assert result["backendValidationStatus"]=="not-run"
    assert result["executionQualification"]=="not-qualified"
    assert not {"compilationStatus","buildStatus","importStatus","testStatus"} & result.keys()
