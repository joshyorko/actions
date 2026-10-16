import hashlib
import os
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).parents[2]
WORKFLOW_PATH = ROOT / ".github" / "workflows" / "http_lib_release.yml"
TOKEN_ENV = "POETRY_PYPI_TOKEN_PYPI"


def _workflow():
    return yaml.safe_load(WORKFLOW_PATH.read_text())


def _step(workflow, job, name):
    return next(
        step for step in workflow["jobs"][job]["steps"] if step.get("name") == name
    )


def _run_shell_step(script, cwd, tmp_path, tag="actions_http-1.0.1"):
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
            "PACKAGE_VERSION": "1.0.1",
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


def test_http_helper_release_verifies_pinned_exact_artifacts_before_publish():
    workflow = _workflow()

    on = workflow.get("on", workflow.get(True))
    assert on["push"]["tags"] == ["actions_http-*"]
    assert workflow["defaults"]["run"]["working-directory"] == "./actions-http-helper"
    verify = workflow["jobs"]["verify"]
    build = _step(workflow, "verify", "Build verified HTTP helper artifacts")
    artifacts = _step(workflow, "verify", "Verify exact HTTP helper artifact inventory")
    twine = _step(workflow, "verify", "Verify HTTP helper artifacts")
    upload = _step(workflow, "verify", "Upload verified HTTP helper artifacts")
    assert verify["steps"][0]["uses"] == (
        "actions/checkout@fbc6f3992d24b796d5a048ff273f7fcc4a7b6c09"
    )
    assert any(
        step.get("run") == "pipx install poetry==2.1.1" for step in verify["steps"]
    )
    assert build["run"] == "poetry build"
    assert " -C " not in build["run"]
    assert '"actions_http_helper-$package_version.tar.gz"' in artifacts["run"]
    assert '"actions_http_helper-$package_version-py3-none-any.whl"' in artifacts["run"]
    assert "find dist -mindepth 1 -maxdepth 1 -printf '%f\\n'" in artifacts["run"]
    assert (
        '"$(find dist -mindepth 1 -maxdepth 1 -type f | wc -l)" -eq 2'
        in artifacts["run"]
    )
    twine_install = _step(workflow, "verify", "Install Twine 6.2.0")
    assert "twine==6.2.0" in twine_install["run"]
    assert "twine check --strict" in twine["run"]
    assert upload["with"]["name"] == "actions-http-helper-dist"
    assert upload["with"]["path"] == "actions-http-helper/dist"

    publish = workflow["jobs"]["publish"]
    assert publish["needs"] == "verify"
    assert publish["environment"] == "pypi"
    download = _step(workflow, "publish", "Download verified HTTP helper artifacts")
    assert download["with"]["name"] == "actions-http-helper-dist"
    verify_copy = _step(workflow, "publish", "Verify downloaded HTTP helper artifacts")
    assert (
        "(cd dist && sha256sum -c actions-http-helper-manifest.sha256)"
        in verify_copy["run"]
    )
    assert "diff -u" in verify_copy["run"]


def test_http_helper_publish_fails_closed_without_token_and_passes_configured_secret_to_child(
    tmp_path,
):
    workflow = _workflow()
    step = _step(workflow, "publish", "Publish verified HTTP helper artifacts")
    assert step["env"] == {TOKEN_ENV: "${{ secrets.PYPI_TOKEN_ACTIONS_HTTP_HELPER }}"}
    script = step["run"]
    assert "PYPI_TOKEN_ACTIONS_HTTP_HELPER is required" in script
    assert "poetry config" not in script
    assert "${{ secrets.PYPI_TOKEN_ACTIONS_HTTP_HELPER }}" not in script

    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    args_file = tmp_path / "args"
    env_file = tmp_path / "child-env"
    poetry = fake_bin / "poetry"
    poetry.write_text(
        "#!/bin/sh\n"
        'printf \'%s\\n\' "$@" > "$ARGS_FILE"\n'
        f'printf \'%s\' "${TOKEN_ENV}" > "$ENV_FILE"\n'
    )
    poetry.chmod(0o755)
    base_env = os.environ.copy()
    base_env.update(
        {
            "PATH": f"{fake_bin}{os.pathsep}{base_env['PATH']}",
            "ARGS_FILE": str(args_file),
            "ENV_FILE": str(env_file),
            "TOKEN_ENV": TOKEN_ENV,
        }
    )

    empty_env = base_env | {TOKEN_ENV: ""}
    empty = subprocess.run(
        ["bash", "-euo", "pipefail", "-c", script],
        env=empty_env,
        capture_output=True,
        text=True,
    )
    assert empty.returncode != 0
    assert "PYPI_TOKEN_ACTIONS_HTTP_HELPER is required" in empty.stderr
    assert not args_file.exists()
    assert not env_file.exists()

    sentinel = "github-actions-test-token-do-not-use"
    configured_env = base_env | {TOKEN_ENV: sentinel}
    configured = subprocess.run(
        ["bash", "-euo", "pipefail", "-c", script],
        env=configured_env,
        capture_output=True,
        text=True,
    )
    assert configured.returncode == 0
    assert args_file.read_text().splitlines() == ["publish", "--no-interaction"]
    assert env_file.read_text() == sentinel
    assert sentinel not in script
    assert sentinel not in configured.stdout
    assert sentinel not in configured.stderr


def test_http_helper_artifact_inventory_and_manifest_bind_exact_bytes(tmp_path):
    workflow = _workflow()
    build_step = _step(
        workflow, "verify", "Verify exact HTTP helper artifact inventory"
    )
    publish_step = _step(workflow, "publish", "Verify downloaded HTTP helper artifacts")
    package_root = tmp_path / "actions-http-helper"
    dist = package_root / "dist"
    dist.mkdir(parents=True)
    wheel = "actions_http_helper-1.0.1-py3-none-any.whl"
    sdist = "actions_http_helper-1.0.1.tar.gz"
    (dist / wheel).write_bytes(b"wheel bytes")
    (dist / sdist).write_bytes(b"sdist bytes")

    built = _run_shell_step(build_step["run"], package_root, tmp_path)
    assert built.returncode == 0, built.stderr
    manifest = (dist / "actions-http-helper-manifest.sha256").read_text()
    expected = {
        name: hashlib.sha256((dist / name).read_bytes()).hexdigest()
        for name in (wheel, sdist)
    }
    assert manifest.splitlines() == [
        f"{expected[name]}  {name}" for name in sorted(expected)
    ]

    downloaded = _run_shell_step(publish_step["run"], package_root, tmp_path)
    assert downloaded.returncode == 0, downloaded.stderr

    (dist / wheel).write_bytes(b"modified wheel bytes")
    tampered = _run_shell_step(publish_step["run"], package_root, tmp_path)
    assert tampered.returncode != 0
    assert "FAILED" in tampered.stdout


def test_http_helper_inventory_rejects_wrong_tag_and_extra_files(tmp_path):
    workflow = _workflow()
    step = _step(workflow, "verify", "Verify exact HTTP helper artifact inventory")
    package_root = tmp_path / "actions-http-helper"
    dist = package_root / "dist"
    dist.mkdir(parents=True)
    (dist / "actions_http_helper-1.0.1-py3-none-any.whl").write_bytes(b"wheel")
    (dist / "actions_http_helper-1.0.1.tar.gz").write_bytes(b"sdist")

    wrong_tag = _run_shell_step(
        step["run"], package_root, tmp_path, tag="actions_http-1.0.0"
    )
    assert wrong_tag.returncode != 0
    assert not (dist / "actions-http-helper-manifest.sha256").exists()

    (dist / "unexpected.bin").write_bytes(b"unexpected")
    extra = _run_shell_step(step["run"], package_root, tmp_path)
    assert extra.returncode != 0
    assert "unexpected.bin" in extra.stdout
