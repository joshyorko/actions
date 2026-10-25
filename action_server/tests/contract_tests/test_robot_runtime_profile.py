"""Host-only Robot preparation configuration; no discovery or implicit fallback."""
import json
from pathlib import Path

import pytest

from actions.server.foundry.robot_runtime_profile import (
    RobotRuntimeProfile,
    read_robot_profile,
)


def test_unconfigured_robot_remains_absent():
    assert read_robot_profile(None) is None


@pytest.mark.parametrize('changes', [
    {}, {'direct_python': 'relative/python'}, {'prepared_receipt': ''},
    {'direct_python': '/owned/python', 'admission': 'implicit'},
    {'direct_python': '/owned/python', 'api_key': 'not-accepted'},
])
def test_closed_explicit_preparation_required(changes):
    value = {'schema_version': 'actions.runtime-robot-profile/v1', 'admission': 'trusted-developer-execution', **changes}
    with pytest.raises(ValueError): RobotRuntimeProfile.model_validate(value)


def test_exact_host_configuration_retained(tmp_path):
    p = tmp_path/'profile.json'
    value = {'schema_version': 'actions.runtime-robot-profile/v1', 'admission': 'trusted-developer-execution', 'direct_python': '/owned/python', 'prepared_receipt': '/owned/prepared.json'}
    p.write_text(json.dumps(value))
    assert read_robot_profile(str(p)).model_dump() == value


def test_duplicate_and_oversized_host_configuration_denied(tmp_path):
    p=tmp_path/'profile.json'
    p.write_text('{"direct_python":"/a","direct_python":"/b"}')
    with pytest.raises(ValueError, match='duplicate'):read_robot_profile(str(p))
    p.write_bytes(b' '*16385)
    with pytest.raises(ValueError, match='bound'):read_robot_profile(str(p))
    with pytest.raises(ValueError, match='absolute'):read_robot_profile('relative.json')
