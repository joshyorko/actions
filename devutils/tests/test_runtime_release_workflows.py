import re
from pathlib import Path

ROOT = Path(__file__).parents[2]
WORKFLOWS = ROOT / ".github" / "workflows"


def test_runtime_release_workflows_have_one_verified_pypi_publisher():
    generator = (WORKFLOWS / "_gen_workflows.py").read_text()
    pypi = (WORKFLOWS / "actions_runtime_pypi_release.yml").read_text()

    assert not (WORKFLOWS / "actions_runtime_manylinux_release.yml").exists()
    assert generator.count('target = "actions_runtime_pypi_release.yml"') == 1
    assert "actions-runtime-*" in pypi
    assert "branches:" not in pypi
    assert pypi.count("PYPI_TOKEN_ACTIONS_RUNTIME") == 1
    assert pypi.count("twine check --strict") == 1
    assert "git merge-base --is-ancestor \"$GITHUB_SHA\" origin/community" in pypi
    assert "poetry version --short" in pypi
    assert "python -m pip check" in pypi
    assert "python -m actions.server version" in pypi
    assert "actions/upload-artifact@" in pypi
    assert "actions/download-artifact@" in pypi
    assert "needs:" in pypi
    assert "Publish verified artifacts" in pypi
    assert "cibuildwheel==2.23.1" in pypi
    assert "twine==6.2.0" in pypi

    publish_job = re.search(r"(?ms)^  publish:\n.*", pypi)
    assert publish_job
    assert "poetry build" not in publish_job.group()
    assert "twine upload" in publish_job.group()
    assert pypi.count("twine upload") == 1


def test_binary_release_uses_explicit_tag_asset_names():
    binary = (WORKFLOWS / "actions_runtime_binary_release.yml").read_text()

    assert "$tag-" not in binary
    assert "asset_name: ${{ github.ref_name }}-linux64" in binary
    assert "asset_name: ${{ github.ref_name }}-macos-arm64" in binary
    assert "asset_name: ${{ github.ref_name }}-windows64.exe" in binary
