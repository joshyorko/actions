import os
from pathlib import Path
from unittest import mock

import actions.server._new_project


def test_create_new_project_uses_embedded_template(tmpdir) -> None:
    from actions.server._new_project import handle_new_project

    templates_path = Path(tmpdir) / "action-templates"
    project_path = Path(tmpdir) / "my_project"
    with mock.patch(
        "actions.server._new_project_helpers._get_action_templates_dir_path",
        return_value=templates_path,
    ):
        assert handle_new_project(project_path, "minimal") == 0

    assert os.path.isfile(project_path / "package.yaml")
    assert os.path.isfile(templates_path / "minimal.zip")


@mock.patch(
    "actions.server._new_project_helpers._ensure_latest_templates",
    side_effect=None,
)
@mock.patch(
    "actions.server._new_project.log.info",
    wraps=actions.server._new_project.log.info,
)
@mock.patch("sys.stdout.buffer.write")
def test_list_templates_no_templates_available(
    print_mock: mock.MagicMock, log_info_mock: mock.MagicMock, _, tmpdir
) -> None:
    from actions.server._new_project import handle_list_templates
    from actions.server._new_project_helpers import ActionTemplatesMetadata

    with mock.patch(
        "actions.server._new_project_helpers._get_local_templates_metadata",
        return_value=ActionTemplatesMetadata(hash="test_hash", templates=[]),
    ):
        assert handle_list_templates() == 0
        assert "No templates available" in log_info_mock.mock_calls[-1].args[0]

        assert handle_list_templates(output_json=True) == 0
        assert print_mock.mock_calls[-1].args[0] == b"[]"


def test_action_server_new_force_flag(datadir):
    from actions.server._selftest import actions_server_run

    project_path = datadir / "my_project"
    project_path.mkdir()
    package_yaml_path = project_path / "package.yaml"
    package_yaml_path.write_text("foo", encoding="utf-8")

    actions_server_run(
        ["new", "--name", "my_project", "--template", "minimal", "--force"],
        returncode=0,
        cwd=datadir,
    )
    assert package_yaml_path.read_text(encoding="utf-8") != "foo"
