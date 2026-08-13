"""Regression coverage for the build-binary top-level import contract."""

import subprocess
import sys
from pathlib import Path

import pytest


def test_artifact_validator_imports_from_build_binary_directory():
    """The task runner imports build-binary helpers as top-level modules."""
    build_binary = Path(__file__).parents[2] / "build-binary"

    result = subprocess.run(
        [sys.executable, "-c", "import artifact_validator"],
        cwd=build_binary,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr


def test_validate_artifact_task_rejects_removed_product_imports(tmp_path, monkeypatch, capsys):
    """The real Invoke task rejects injected imports in a built artifact."""
    action_server = Path(__file__).parents[2]
    sys.path.insert(0, str(action_server))
    import tasks
    from invoke import Context

    dist = tmp_path / "frontend" / "dist"
    dist.mkdir(parents=True)
    (tmp_path / "build-binary").symlink_to(action_server / "build-binary")
    (dist / "index.js").write_text(
        "import '@sema4ai/components';\n"
        "import '@/enterprise/private';\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(tasks, "CURDIR", tmp_path)

    with pytest.raises(SystemExit) as raised:
        tasks.validate_artifact.body(Context(), json_output=False)

    assert raised.value.code == 2
    output = capsys.readouterr().out
    assert "@sema4ai/components" in output
    assert "@/enterprise/private" in output


def test_validate_artifact_task_accepts_clean_artifact(tmp_path, monkeypatch):
    """The real Invoke task accepts an artifact with public imports."""
    action_server = Path(__file__).parents[2]
    sys.path.insert(0, str(action_server))
    import tasks
    from invoke import Context

    dist = tmp_path / "frontend" / "dist"
    dist.mkdir(parents=True)
    (tmp_path / "build-binary").symlink_to(action_server / "build-binary")
    (dist / "index.js").write_text(
        "import '@radix-ui/react-dialog';\n", encoding="utf-8"
    )
    monkeypatch.setattr(tasks, "CURDIR", tmp_path)

    tasks.validate_artifact.body(Context(), json_output=False)
