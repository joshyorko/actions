import hashlib
import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[3]
WORKFLOW_PATH = ROOT / ".github" / "workflows" / "actions_release.yml"
TOKEN_ENV = "POETRY_PYPI_TOKEN_PYPI"
LINUX_RELEASE_SHELL_ONLY = pytest.mark.skipif(
    sys.platform != "linux",
    reason="Core release workflow shell runs on ubuntu-latest with GNU utilities",
)


def _workflow():
    return yaml.safe_load(WORKFLOW_PATH.read_text())


def _step(workflow, job, name):
    return next(
        step for step in workflow["jobs"][job]["steps"] if step.get("name") == name
    )


def _run_shell_step(script, cwd, tmp_path, tag="actions-core-1.0.2"):
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir(exist_ok=True)
    poetry = fake_bin / "poetry"
    poetry.write_text(
        "#!/bin/sh\n"
        'test "$1 $2" = "version --short"\n'
        "printf '%s\\n' \"$PACKAGE_VERSION\"\n"
    )
    poetry.chmod(0o755)
    base_env = os.environ.copy()
    base_env.update(
        {
            "PATH": f"{fake_bin}{os.pathsep}{base_env['PATH']}",
            "PACKAGE_VERSION": "1.0.2",
            "GITHUB_REF_NAME": tag,
        }
    )
    return subprocess.run(
        ["bash", "-euo", "pipefail", "-c", script],
        cwd=cwd,
        env=base_env,
        capture_output=True,
        text=True,
    )


def test_core_release_verifies_pinned_exact_artifacts_before_publish():
    workflow = _workflow()
    on = workflow.get("on", workflow.get(True))
    assert on["push"]["tags"] == ["actions-core-*"]
    assert workflow["defaults"]["run"]["working-directory"] == "./actions"
    verify = workflow["jobs"]["verify"]
    assert verify["runs-on"] == "ubuntu-latest"
    build = _step(workflow, "verify", "Build verified Core artifacts")
    inventory = _step(workflow, "verify", "Verify exact Core artifact inventory")
    twine = _step(workflow, "verify", "Verify Core artifacts")
    clean_wheel = _step(workflow, "verify", "Verify clean installed Core wheel")
    upload = _step(workflow, "verify", "Upload verified Core artifacts")

    assert any(
        step.get("run") == "pipx install poetry==2.1.1" for step in verify["steps"]
    )
    assert build["run"] == "poetry build"
    assert '"actions_core-$package_version.tar.gz"' in inventory["run"]
    assert '"actions_core-$package_version-py3-none-any.whl"' in inventory["run"]
    assert "find dist -mindepth 1 -maxdepth 1 -printf '%f\\n'" in inventory["run"]
    assert (
        '"$(find dist -mindepth 1 -maxdepth 1 -type f | wc -l)" -eq 2'
        in inventory["run"]
    )
    assert "sha256sum dist/*.whl dist/*.tar.gz" in inventory["run"]
    assert "twine==6.2.0" in _step(workflow, "verify", "Install Twine 6.2.0")["run"]
    assert "twine check --strict" in twine["run"]
    assert "verify_clean_wheel.py" in clean_wheel["run"]
    assert upload["with"]["name"] == "actions-core-dist"
    assert upload["with"]["path"] == "actions/dist"

    publish = workflow["jobs"]["publish"]
    assert publish["runs-on"] == "ubuntu-latest"
    assert publish["needs"] == "verify"
    assert publish["environment"] == "pypi"
    assert (
        _step(workflow, "publish", "Download verified Core artifacts")["with"]["name"]
        == "actions-core-dist"
    )
    downloaded = _step(workflow, "publish", "Verify downloaded Core artifacts")
    assert "actions-core-manifest.sha256" in downloaded["run"]
    assert "(cd dist && sha256sum -c actions-core-manifest.sha256)" in downloaded["run"]
    assert "diff -u" in downloaded["run"]


@LINUX_RELEASE_SHELL_ONLY
def test_core_artifact_inventory_and_manifest_bind_exact_bytes(tmp_path):
    workflow = _workflow()
    build_step = _step(workflow, "verify", "Verify exact Core artifact inventory")
    publish_step = _step(workflow, "publish", "Verify downloaded Core artifacts")
    package_root = tmp_path / "actions"
    dist = package_root / "dist"
    dist.mkdir(parents=True)
    wheel = "actions_core-1.0.2-py3-none-any.whl"
    sdist = "actions_core-1.0.2.tar.gz"
    (dist / wheel).write_bytes(b"wheel bytes")
    (dist / sdist).write_bytes(b"sdist bytes")

    built = _run_shell_step(build_step["run"], package_root, tmp_path)
    assert built.returncode == 0, built.stderr
    expected = {
        name: hashlib.sha256((dist / name).read_bytes()).hexdigest()
        for name in (wheel, sdist)
    }
    assert (dist / "actions-core-manifest.sha256").read_text().splitlines() == [
        f"{expected[name]}  {name}" for name in sorted(expected)
    ]

    downloaded = _run_shell_step(publish_step["run"], package_root, tmp_path)
    assert downloaded.returncode == 0, downloaded.stderr

    (dist / wheel).write_bytes(b"modified wheel bytes")
    tampered = _run_shell_step(publish_step["run"], package_root, tmp_path)
    assert tampered.returncode != 0
    assert "FAILED" in tampered.stdout


@LINUX_RELEASE_SHELL_ONLY
def test_core_inventory_rejects_wrong_tag_extra_and_symlink_artifacts(tmp_path):
    workflow = _workflow()
    step = _step(workflow, "verify", "Verify exact Core artifact inventory")
    package_root = tmp_path / "actions"
    dist = package_root / "dist"
    dist.mkdir(parents=True)
    (dist / "actions_core-1.0.2-py3-none-any.whl").write_bytes(b"wheel")
    (dist / "actions_core-1.0.2.tar.gz").write_bytes(b"sdist")

    wrong_tag = _run_shell_step(
        step["run"], package_root, tmp_path, tag="actions-core-1.0.1"
    )
    assert wrong_tag.returncode != 0
    assert not (dist / "actions-core-manifest.sha256").exists()

    (dist / "unexpected.bin").write_bytes(b"unexpected")
    extra = _run_shell_step(step["run"], package_root, tmp_path)
    assert extra.returncode != 0
    assert "unexpected.bin" in extra.stdout

    (dist / "unexpected.bin").unlink()
    (dist / "actions_core-1.0.2-py3-none-any.whl").unlink()
    outside = tmp_path / "outside.whl"
    outside.write_bytes(b"outside wheel")
    (dist / "actions_core-1.0.2-py3-none-any.whl").symlink_to(outside)
    symlink = _run_shell_step(step["run"], package_root, tmp_path)
    assert symlink.returncode != 0


@LINUX_RELEASE_SHELL_ONLY
def test_core_publish_fails_closed_without_token(tmp_path):
    workflow = _workflow()
    step = _step(workflow, "publish", "Publish verified Core artifacts")
    assert step["env"] == {TOKEN_ENV: "${{ secrets.PYPI_TOKEN_ACTIONS_CORE }}"}
    assert "PYPI_TOKEN_ACTIONS_CORE is required" in step["run"]
    assert "poetry config" not in step["run"]
    assert "${{ secrets.PYPI_TOKEN_ACTIONS_CORE }}" not in step["run"]

    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    args_file = tmp_path / "args"
    poetry = fake_bin / "poetry"
    poetry.write_text("#!/bin/sh\n" 'printf \'%s\\n\' "$@" > "$ARGS_FILE"\n')
    poetry.chmod(0o755)
    base_env = os.environ.copy()
    base_env.update(
        {
            "PATH": f"{fake_bin}{os.pathsep}{base_env['PATH']}",
            "ARGS_FILE": str(args_file),
        }
    )

    empty = subprocess.run(
        ["bash", "-euo", "pipefail", "-c", step["run"]],
        env=base_env | {TOKEN_ENV: ""},
        capture_output=True,
        text=True,
    )
    assert empty.returncode != 0
    assert "PYPI_TOKEN_ACTIONS_CORE is required" in empty.stderr
    assert not args_file.exists()

    sentinel = "github-actions-test-token-do-not-use"
    configured = subprocess.run(
        ["bash", "-euo", "pipefail", "-c", step["run"]],
        env=base_env | {TOKEN_ENV: sentinel},
        capture_output=True,
        text=True,
    )
    assert configured.returncode == 0
    assert args_file.read_text().splitlines() == ["publish", "--no-interaction"]
    assert sentinel not in step["run"]
    assert sentinel not in configured.stdout
    assert sentinel not in configured.stderr
