import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

FRONTEND = Path(__file__).parents[2] / "frontend"


def test_frontend_manifest_declares_modern_dual_artifact_contract():
    manifest = json.loads((FRONTEND / "package.json").read_text())

    assert manifest["engines"]["node"] == ">=20.19.0"
    assert "build:artifacts" in manifest["scripts"]
    assert "validate:artifacts" in manifest["scripts"]
    assert "@vitejs/plugin-react" in manifest["devDependencies"]
    assert "vite-plugin-singlefile" not in manifest["devDependencies"]


def test_vite_config_keeps_runtime_embeddable_and_canvas_mcp_view_distinct():
    config = (FRONTEND / "vite.config.js").read_text()

    assert "runtime-admin" in config
    assert "canvas-mcp-app" in config
    assert "sourcemap: false" in config
    assert "text/html;profile=mcp-app" in config


def test_artifact_validator_checks_manifests_and_directory_budgets():
    validator = (FRONTEND.parent / "build-binary" / "artifact_validator.py").read_text()

    assert "artifact-manifest.json" in validator
    assert "sbom.json" in validator
    assert "rglob" in validator
    assert "expected_artifact" in validator
    assert "expected_content_type" in validator


def test_hosted_bundle_budget_uses_the_manifest_payload_for_both_artifacts():
    workflow = (FRONTEND.parents[1] / ".github/workflows/frontend-build.yml").read_text()

    assert "npm run validate:artifacts" in workflow
    assert "du -sb dist" not in workflow
    assert "Get-ChildItem -Path dist -Recurse -File" not in workflow


def test_frontend_release_metadata_and_canvas_identity_are_cross_platform():
    package = json.loads((FRONTEND / "package.json").read_text())
    scripts = package["scripts"]

    assert scripts["sbom"].count("--output-reproducible") == 2
    assert "'text/html;profile=mcp-app'" not in scripts["build:canvas"]
    assert '"text/html;profile=mcp-app"' in scripts["build:canvas"]


def test_hosted_determinism_check_covers_every_matrix_os():
    workflow = (FRONTEND.parents[1] / ".github/workflows/frontend-build.yml").read_text()

    assert "if: runner.os != 'Windows'" not in workflow


def test_hosted_workflow_runs_frontend_quality_and_compares_both_roots():
    workflow = (FRONTEND.parents[1] / ".github/workflows/frontend-build.yml").read_text()

    assert "npm run test:quality" in workflow
    assert "dist-canvas" in workflow
    assert "relative" in workflow or "relpath" in workflow
    assert "sha256sum" not in workflow

    validator = (FRONTEND / "scripts/validate-artifacts.mjs").read_text()
    assert "createHash('sha256')" in validator
    assert "bytes.length !== file.bytes" in validator
    assert "actualFiles" in validator


def test_hosted_determinism_block_closes_heredoc_before_restoring_artifacts():
    workflow = (FRONTEND.parents[1] / ".github/workflows/frontend-build.yml").read_text()
    python_start = workflow.index("          python - <<'PY'")
    heredoc_end = workflow.index("          PY\n", python_start)
    restoration = workflow.index("          rm -rf frontend/dist", heredoc_end)

    assert heredoc_end > python_start
    assert restoration > heredoc_end


def test_frontend_quality_uses_cross_platform_prettier_eol_contract():
    package = json.loads((FRONTEND / "package.json").read_text())
    scripts = package["scripts"]

    assert scripts["test:prettier"] == (
        "prettier --end-of-line auto --check "
        "apps/runtime/src apps/canvas-view/src src/app"
    )
    assert scripts["test:quality"] == (
        "npm run test:lint && npm run test:types && "
        "npm run test:prettier && npm run test:topology"
    )
    assert scripts["test:topology"] == (
        'vitest --run --testNamePattern "Actions frontend topology"'
    )
    vite_config = (FRONTEND / "vite.config.js").read_text()
    assert "replaceAll(path.sep, '/')" in vite_config


def test_validators_prove_manifest_inventory_and_metadata(tmp_path):
    build_binary = FRONTEND.parent / "build-binary"
    sys.path.insert(0, str(build_binary))
    from artifact_validator import validate_build_metadata

    root = tmp_path / "artifact"
    root.mkdir()
    (root / "index.html").write_bytes(b"runtime")
    (root / "extra.js").write_bytes(b"extra")
    (root / "omitted.js").write_bytes(b"omitted")
    files = [
        {"path": "extra.js", "bytes": 999, "sha256": "0" * 64},
        {"path": "index.html", "bytes": 999, "sha256": "1" * 64},
    ]
    (root / "artifact-manifest.json").write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "artifact": "runtime-admin",
                "contentType": "text/html",
                "sourceMaps": False,
                "files": files,
            }
        ),
        encoding="utf-8",
    )
    (root / "sbom.json").write_text("{}", encoding="utf-8")

    checks = validate_build_metadata(root)

    assert not all(check.passed for check in checks)
    assert any(check.name == "inventory" and not check.passed for check in checks)
    assert any(check.name == "hashes" and not check.passed for check in checks)
    assert any(check.name == "sizes" and not check.passed for check in checks)


@pytest.mark.parametrize("mutation", ["omission", "extra", "path-swap", "reorder"])
def test_manifest_contract_rejects_inventory_mutations(tmp_path, mutation):
    build_binary = FRONTEND.parent / "build-binary"
    sys.path.insert(0, str(build_binary))
    from artifact_validator import validate_build_metadata

    root = tmp_path / "artifact"
    root.mkdir()
    contents = {"a.txt": b"a", "b.txt": b"b"}
    for name, content in contents.items():
        (root / name).write_bytes(content)
    files = [
        {"path": name, "bytes": len(content), "sha256": hashlib.sha256(content).hexdigest()}
        for name, content in contents.items()
    ]
    if mutation == "omission":
        files.pop()
    elif mutation == "extra":
        files.append({"path": "missing.txt", "bytes": 0, "sha256": "0" * 64})
    elif mutation == "path-swap":
        files[0]["path"], files[1]["path"] = files[1]["path"], files[0]["path"]
    elif mutation == "reorder":
        files.reverse()
    (root / "artifact-manifest.json").write_text(
        json.dumps({"schemaVersion": 1, "contentType": "text/html", "files": files}),
        encoding="utf-8",
    )
    (root / "sbom.json").write_text("{}", encoding="utf-8")

    checks = validate_build_metadata(root)

    assert any(not check.passed for check in checks)


def _write_manifest(root, artifact, content_type, files):
    (root / "artifact-manifest.json").write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "artifact": artifact,
                "contentType": content_type,
                "sourceMaps": False,
                "files": files,
            }
        ),
        encoding="utf-8",
    )
    (root / "sbom.json").write_text("{}", encoding="utf-8")


@pytest.mark.parametrize("link_kind", ["file", "directory", "broken"])
def test_python_validator_rejects_symlink_payload_and_root_aliases(
    tmp_path, link_kind
):
    build_binary = FRONTEND.parent / "build-binary"
    sys.path.insert(0, str(build_binary))
    from artifact_validator import validate_build_metadata

    root = tmp_path / "runtime"
    root.mkdir()
    payload = root / "index.html"
    payload.write_text("runtime", encoding="utf-8")
    if link_kind == "file":
        (root / "payload.js").symlink_to(payload)
    elif link_kind == "directory":
        target_dir = tmp_path / "target"
        target_dir.mkdir()
        (target_dir / "payload.js").write_text("runtime", encoding="utf-8")
        (root / "payload-dir").symlink_to(target_dir, target_is_directory=True)
    else:
        (root / "broken.js").symlink_to(tmp_path / "missing.js")
    files = [
        {
            "path": "index.html",
            "bytes": 7,
            "sha256": hashlib.sha256(b"runtime").hexdigest(),
        }
    ]
    _write_manifest(root, "runtime-admin", "text/html", files)

    checks = validate_build_metadata(root, "runtime-admin", "text/html")

    assert any(check.name == "symlinks" and not check.passed for check in checks)
    alias = tmp_path / "runtime-alias"
    alias.symlink_to(root, target_is_directory=True)
    alias_checks = validate_build_metadata(alias, "runtime-admin", "text/html")
    assert any(check.name == "symlinks" and not check.passed for check in alias_checks)


@pytest.mark.parametrize(
    "declared_artifact,declared_type,expected_artifact,expected_type",
    [
        (
            "runtime-admin",
            "text/html",
            "canvas-mcp-app",
            "text/html;profile=mcp-app",
        ),
        (
            "canvas-mcp-app",
            "text/html;profile=mcp-app",
            "runtime-admin",
            "text/html",
        ),
    ],
)
def test_python_validator_binds_artifact_identity_and_content_type(
    tmp_path, declared_artifact, declared_type, expected_artifact, expected_type
):
    build_binary = FRONTEND.parent / "build-binary"
    sys.path.insert(0, str(build_binary))
    from artifact_validator import validate_build_metadata

    root = tmp_path / "artifact"
    root.mkdir()
    payload = b"<html></html>"
    (root / "index.html").write_bytes(payload)
    _write_manifest(
        root,
        declared_artifact,
        declared_type,
        [{"path": "index.html", "bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}],
    )

    checks = validate_build_metadata(root, expected_artifact, expected_type)

    assert any(check.name == "artifact" and not check.passed for check in checks)
    assert any(check.name == "content-type" and not check.passed for check in checks)
    unbound_checks = validate_build_metadata(root)
    assert any(check.name == "artifact" and not check.passed for check in unbound_checks)
    assert any(check.name == "content-type" and not check.passed for check in unbound_checks)


@pytest.mark.parametrize(
    "link_kind", ["file", "directory", "broken"]
)
@pytest.mark.parametrize(
    "directory,artifact,content_type",
    [
        ("dist", "runtime-admin", "text/html"),
        ("dist-canvas", "canvas-mcp-app", "text/html;profile=mcp-app"),
    ],
)
def test_javascript_validator_rejects_symlink_payload(
    tmp_path, directory, artifact, content_type, link_kind
):
    script = FRONTEND / "scripts" / "validate-artifacts.mjs"
    for current_directory, current_artifact, current_content_type in (
        ("dist", "runtime-admin", "text/html"),
        ("dist-canvas", "canvas-mcp-app", "text/html;profile=mcp-app"),
    ):
        root = tmp_path / current_directory
        root.mkdir()
        payload = f"<html>{current_content_type}</html>".encode()
        (root / "index.html").write_bytes(payload)
        files = [
            {
                "path": "index.html",
                "bytes": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
            }
        ]
        if current_directory == directory:
            if link_kind == "file":
                (root / "payload.js").symlink_to(root / "index.html")
            elif link_kind == "directory":
                target_dir = tmp_path / "target"
                target_dir.mkdir()
                (target_dir / "payload.js").write_bytes(payload)
                (root / "payload-dir").symlink_to(
                    target_dir, target_is_directory=True
                )
            else:
                (root / "broken.js").symlink_to(tmp_path / "missing.js")
        _write_manifest(
            root,
            current_artifact,
            current_content_type,
            files,
        )

    result = subprocess.run(
        ["node", str(script)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert directory in (result.stderr + result.stdout)
    assert "symlink" in (result.stderr + result.stdout).lower()


def test_javascript_validator_rejects_symlink_root(tmp_path):
    script = FRONTEND / "scripts" / "validate-artifacts.mjs"
    runtime = tmp_path / "runtime-root"
    runtime.mkdir()
    payload = b"<html>text/html</html>"
    (runtime / "index.html").write_bytes(payload)
    _write_manifest(
        runtime,
        "runtime-admin",
        "text/html",
        [{"path": "index.html", "bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}],
    )
    (tmp_path / "dist").symlink_to(runtime, target_is_directory=True)
    canvas = tmp_path / "dist-canvas"
    canvas.mkdir()
    canvas_payload = b"<html>text/html;profile=mcp-app</html>"
    (canvas / "index.html").write_bytes(canvas_payload)
    _write_manifest(
        canvas,
        "canvas-mcp-app",
        "text/html;profile=mcp-app",
        [{"path": "index.html", "bytes": len(canvas_payload), "sha256": hashlib.sha256(canvas_payload).hexdigest()}],
    )

    result = subprocess.run(
        ["node", str(script)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "dist" in (result.stderr + result.stdout)
    assert "symlink root" in (result.stderr + result.stdout).lower()


def test_invoke_validator_rejects_explicit_root_alias_before_resolution(
    tmp_path, monkeypatch
):
    action_server = FRONTEND.parent
    sys.path.insert(0, str(action_server))
    import tasks
    from invoke import Context

    runtime = tmp_path / "runtime"
    canvas = tmp_path / "canvas"
    runtime.mkdir()
    canvas.mkdir()
    (runtime / "index.html").write_text("runtime", encoding="utf-8")
    (canvas / "index.html").write_text("canvas", encoding="utf-8")
    (tmp_path / "runtime-alias").symlink_to(runtime, target_is_directory=True)
    (tmp_path / "build-binary").symlink_to(action_server / "build-binary")
    monkeypatch.setattr(tasks, "CURDIR", tmp_path)

    with pytest.raises(SystemExit) as raised:
        tasks.validate_artifact.body(
            Context(),
            runtime_artifact=str(tmp_path / "runtime-alias"),
            canvas_artifact=str(canvas),
            json_output=False,
        )

    assert raised.value.code == 2


def test_hosted_import_validator_rejects_poisoned_canvas_root(
    tmp_path, monkeypatch, capsys
):
    action_server = FRONTEND.parent
    sys.path.insert(0, str(action_server))
    import tasks
    from invoke import Context

    runtime = tmp_path / "frontend" / "dist"
    canvas = tmp_path / "frontend" / "dist-canvas"
    runtime.mkdir(parents=True)
    canvas.mkdir()
    (runtime / "index.html").write_text("runtime", encoding="utf-8")
    (canvas / "index.html").write_text(
        'import "@/enterprise/private";', encoding="utf-8"
    )
    (tmp_path / "build-binary").symlink_to(action_server / "build-binary")
    monkeypatch.setattr(tasks, "CURDIR", tmp_path)

    with pytest.raises(SystemExit) as raised:
        tasks.validate_imports.body(Context(), json_output=False)

    assert raised.value.code == 2
    output = capsys.readouterr().out
    assert "Canvas" in output
    assert "@/enterprise/private" in output


def test_hosted_import_validator_rejects_canvas_symlink_before_scanning(
    tmp_path, monkeypatch, capsys
):
    action_server = FRONTEND.parent
    sys.path.insert(0, str(action_server))
    import tasks
    from invoke import Context

    runtime = tmp_path / "frontend" / "dist"
    canvas = tmp_path / "frontend" / "dist-canvas"
    runtime.mkdir(parents=True)
    canvas.mkdir()
    (runtime / "index.html").write_text("runtime", encoding="utf-8")
    target = tmp_path / "safe.js"
    target.write_text('import "react";', encoding="utf-8")
    (canvas / "linked.js").symlink_to(target)
    (tmp_path / "build-binary").symlink_to(action_server / "build-binary")
    monkeypatch.setattr(tasks, "CURDIR", tmp_path)

    with pytest.raises(SystemExit) as raised:
        tasks.validate_imports.body(Context(), json_output=False)

    assert raised.value.code == 2
    assert "symlink" in capsys.readouterr().out.lower()
