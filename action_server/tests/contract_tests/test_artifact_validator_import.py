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


def test_validate_artifact_task_rejects_removed_product_imports(
    tmp_path, monkeypatch, capsys
):
    """The real Invoke task rejects injected imports in a built artifact."""
    action_server = Path(__file__).parents[2]
    sys.path.insert(0, str(action_server))
    import tasks
    from invoke import Context

    dist = tmp_path / "frontend" / "dist"
    dist.mkdir(parents=True)
    (tmp_path / "frontend" / "dist-canvas").mkdir()
    (tmp_path / "build-binary").symlink_to(action_server / "build-binary")
    (dist / "index.js").write_text(
        "import '@sema4ai/components';\n" "import '@/enterprise/private';\n",
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
    canvas = tmp_path / "frontend" / "dist-canvas"
    dist.mkdir(parents=True)
    canvas.mkdir()
    (tmp_path / "build-binary").symlink_to(action_server / "build-binary")
    (dist / "index.js").write_text(
        "import '@radix-ui/react-dialog';\n", encoding="utf-8"
    )
    monkeypatch.setattr(tasks, "CURDIR", tmp_path)

    tasks.validate_artifact.body(Context(), json_output=False)


def test_validate_artifact_builds_missing_default_canvas_once(tmp_path, monkeypatch):
    """The default task repairs a missing Canvas artifact before validation."""
    action_server = Path(__file__).parents[2]
    sys.path.insert(0, str(action_server))
    import tasks
    from invoke import Context

    dist = tmp_path / "frontend" / "dist"
    canvas = tmp_path / "frontend" / "dist-canvas"
    dist.mkdir(parents=True)
    (dist / "index.js").write_text("import 'react';", encoding="utf-8")
    (tmp_path / "build-binary").symlink_to(action_server / "build-binary")
    monkeypatch.setattr(tasks, "CURDIR", tmp_path)
    commands = []

    def build_canvas(ctx, *args, **kwargs):
        commands.append(args)
        canvas.mkdir()
        (canvas / "index.js").write_text("import 'react';", encoding="utf-8")

    monkeypatch.setattr(tasks, "run", build_canvas)

    tasks.validate_artifact.body(Context(), json_output=False)

    assert commands == [("npm", "run", "build:canvas")]


def test_validate_artifact_propagates_default_canvas_build_failure(
    tmp_path, monkeypatch
):
    """A failed owned Canvas build must stop validation."""
    action_server = Path(__file__).parents[2]
    sys.path.insert(0, str(action_server))
    import tasks
    from invoke import Context

    dist = tmp_path / "frontend" / "dist"
    dist.mkdir(parents=True)
    (dist / "index.js").write_text("import 'react';", encoding="utf-8")
    (tmp_path / "build-binary").symlink_to(action_server / "build-binary")
    monkeypatch.setattr(tasks, "CURDIR", tmp_path)
    monkeypatch.setattr(
        tasks,
        "run",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            RuntimeError("Canvas build failed")
        ),
    )

    with pytest.raises(RuntimeError, match="Canvas build failed"):
        tasks.validate_artifact.body(Context(), json_output=False)


def test_validate_artifact_does_not_build_explicit_missing_root(tmp_path, monkeypatch):
    """Explicit artifact roots are validation-only and fail when missing."""
    action_server = Path(__file__).parents[2]
    sys.path.insert(0, str(action_server))
    import tasks
    from invoke import Context

    runtime = tmp_path / "runtime"
    canvas = tmp_path / "canvas"
    runtime.mkdir()
    canvas.mkdir()
    (runtime / "index.js").write_text("import 'react';", encoding="utf-8")
    (canvas / "index.js").write_text("import 'react';", encoding="utf-8")
    (tmp_path / "build-binary").symlink_to(action_server / "build-binary")
    monkeypatch.setattr(tasks, "CURDIR", tmp_path)
    monkeypatch.setattr(
        tasks,
        "run",
        lambda *args, **kwargs: pytest.fail("explicit roots must not build"),
    )

    with pytest.raises(SystemExit) as raised:
        tasks.validate_artifact.body(
            Context(),
            runtime_artifact=str(tmp_path / "missing-runtime"),
            canvas_artifact=str(canvas),
            json_output=False,
        )

    assert raised.value.code == 2


def test_validate_artifact_task_rejects_poisoned_runtime_html(
    tmp_path, monkeypatch, capsys
):
    """The default task scans Runtime HTML, not only JavaScript."""
    action_server = Path(__file__).parents[2]
    sys.path.insert(0, str(action_server))
    import tasks
    from invoke import Context

    dist = tmp_path / "frontend" / "dist"
    canvas = tmp_path / "frontend" / "dist-canvas"
    dist.mkdir(parents=True)
    canvas.mkdir()
    (dist / "index.html").write_text('"@sema4ai/components"', encoding="utf-8")
    (tmp_path / "build-binary").symlink_to(action_server / "build-binary")
    monkeypatch.setattr(tasks, "CURDIR", tmp_path)

    with pytest.raises(SystemExit) as raised:
        tasks.validate_artifact.body(Context(), json_output=False)

    assert raised.value.code == 2
    assert "@sema4ai/components" in capsys.readouterr().out


def test_validate_artifact_task_rejects_poisoned_canvas_html(
    tmp_path, monkeypatch, capsys
):
    """The default task scans Canvas independently of Runtime."""
    action_server = Path(__file__).parents[2]
    sys.path.insert(0, str(action_server))
    import tasks
    from invoke import Context

    dist = tmp_path / "frontend" / "dist"
    canvas = tmp_path / "frontend" / "dist-canvas"
    dist.mkdir(parents=True)
    canvas.mkdir()
    (canvas / "index.html").write_text('"@sema4ai/components"', encoding="utf-8")
    (tmp_path / "build-binary").symlink_to(action_server / "build-binary")
    monkeypatch.setattr(tasks, "CURDIR", tmp_path)

    with pytest.raises(SystemExit) as raised:
        tasks.validate_artifact.body(Context(), json_output=False)

    assert raised.value.code == 2
    assert "dist-canvas" in capsys.readouterr().out


def test_validate_artifact_task_rejects_poisoned_enterprise_path(
    tmp_path, monkeypatch, capsys
):
    """The default task cannot bypass validation with an enterprise path."""
    action_server = Path(__file__).parents[2]
    sys.path.insert(0, str(action_server))
    import tasks
    from invoke import Context

    dist = tmp_path / "frontend" / "dist"
    canvas = tmp_path / "frontend" / "dist-canvas"
    (dist / "enterprise").mkdir(parents=True)
    canvas.mkdir(parents=True)
    (dist / "enterprise" / "index.js").write_text(
        "import '@sema4ai/components';", encoding="utf-8"
    )
    (tmp_path / "build-binary").symlink_to(action_server / "build-binary")
    monkeypatch.setattr(tasks, "CURDIR", tmp_path)

    with pytest.raises(SystemExit) as raised:
        tasks.validate_artifact.body(Context(), json_output=False)

    assert raised.value.code == 2
    assert "@sema4ai/components" in capsys.readouterr().out


def test_validate_artifact_task_fails_closed_on_read_error(tmp_path, monkeypatch):
    """The default task fails when an artifact source file cannot be read."""
    action_server = Path(__file__).parents[2]
    sys.path.insert(0, str(action_server))
    import tasks
    from invoke import Context

    dist = tmp_path / "frontend" / "dist"
    canvas = tmp_path / "frontend" / "dist-canvas"
    dist.mkdir(parents=True)
    canvas.mkdir()
    (dist / "index.js").write_text("import 'react';", encoding="utf-8")
    (tmp_path / "build-binary").symlink_to(action_server / "build-binary")
    monkeypatch.setattr(tasks, "CURDIR", tmp_path)

    import builtins

    original_open = builtins.open

    def fail_runtime_file(path, *args, **kwargs):
        if Path(path) == dist / "index.js":
            raise PermissionError("permission denied")
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", fail_runtime_file)

    with pytest.raises(SystemExit) as raised:
        tasks.validate_artifact.body(Context(), json_output=False)

    assert raised.value.code == 2
