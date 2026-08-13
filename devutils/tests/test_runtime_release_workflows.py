import re
from pathlib import Path

import yaml

ROOT = Path(__file__).parents[2]
WORKFLOWS = ROOT / ".github" / "workflows"


def test_runtime_release_workflows_have_one_verified_pypi_publisher():
    generator = (WORKFLOWS / "_gen_workflows.py").read_text()
    pypi = (WORKFLOWS / "actions_runtime_pypi_release.yml").read_text()

    assert not (WORKFLOWS / "actions_runtime_manylinux_release.yml").exists()
    assert generator.count('target = "actions_runtime_pypi_release.yml"') == 1
    assert "class ActionServerManylinuxRelease" not in generator
    assert "upload_wheels_to_pypi" not in generator
    assert "actions-runtime-*" in pypi
    assert "branches:" not in pypi
    assert generator.count("PYPI_TOKEN_ACTIONS_RUNTIME") == 1
    assert pypi.count("PYPI_TOKEN_ACTIONS_RUNTIME") == 1
    assert pypi.count("twine check --strict") == 1
    assert "git fetch origin community:refs/remotes/origin/community" in pypi
    assert 'git merge-base --is-ancestor "$GITHUB_SHA" origin/community' in pypi
    assert "poetry version --short" in pypi
    assert "python -m pip check" in pypi
    assert "python -m actions.server version" in pypi
    assert "actions/upload-artifact@" in pypi
    assert "actions/download-artifact@" in pypi
    assert "needs:" in pypi
    assert "Publish verified artifacts" in pypi
    assert "cibuildwheel==2.23.1" in pypi
    assert "twine==6.2.0" in pypi
    assert "cp312-*macos*arm64" in pypi
    assert "cp313-*macos*arm64" in pypi
    assert "cp312-*manylinux*x86_64" in pypi
    assert "cp313-*manylinux*x86_64" in pypi
    assert "cp312-*win*amd64" in pypi
    assert "cp313-*win*amd64" in pypi

    workflow = yaml.safe_load(pypi)
    wheel_matrix = workflow["jobs"]["build-wheels"]["strategy"]["matrix"]
    assert [row["name"] for row in wheel_matrix["include"]] == [
        "ubuntu",
        "windows",
        "macos",
    ]
    assert all("-devmode" not in row["name"] for row in wheel_matrix["include"])

    publish_job = re.search(r"(?ms)^  publish:\n.*", pypi)
    assert publish_job
    assert "poetry build" not in publish_job.group()
    assert "name: action-server-dist" in publish_job.group()
    assert "pattern: '*-wheels'" in publish_job.group()
    assert "merge-multiple: true" in publish_job.group()
    assert "twine upload" in publish_job.group()
    assert pypi.count("twine upload") == 1
    assert "name: actions-runtime-dist" in publish_job.group()
    assert "actions/upload-artifact@" in publish_job.group()
    assert "if: steps.runtime-token.outputs.enabled == 'true'" in publish_job.group()
    assert (
        "RUNTIME_TOKEN: ${{ secrets.PYPI_TOKEN_ACTIONS_RUNTIME }}"
        in publish_job.group()
    )
    assert "GITHUB_OUTPUT" in publish_job.group()
    assert publish_job.group().index(
        "Verify Runtime artifacts"
    ) < publish_job.group().index("actions-runtime-dist")
    assert publish_job.group().count("name: actions-runtime-dist") == 1


def test_binary_release_uses_explicit_tag_asset_names():
    binary = (WORKFLOWS / "actions_runtime_binary_release.yml").read_text()

    assert "$tag-" not in binary
    assert "asset_name: ${{ github.ref_name }}-linux64" in binary
    assert "asset_name: ${{ github.ref_name }}-macos-arm64" in binary
    assert "asset_name: ${{ github.ref_name }}-windows64.exe" in binary
