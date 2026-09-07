import hashlib
import json
import os
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


def test_each_default_build_script_emits_its_own_release_sbom():
    scripts = json.loads((FRONTEND / "package.json").read_text())["scripts"]

    assert "npm run sbom:runtime" in scripts["build:runtime"]
    assert "npm run sbom:canvas" in scripts["build:canvas"]
    assert scripts["build:artifacts"] == (
        "npm run build:runtime && npm run build:canvas"
    )


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
        "npm run test:prettier && npm run test:topology && "
        "npm run test:ui-system"
    )
    assert scripts["test:topology"] == (
        'vitest --run --testNamePattern "Actions frontend topology"'
    )
    vite_config = (FRONTEND / "vite.config.js").read_text()
    assert "replaceAll(path.sep, '/')" in vite_config


def test_hosted_quality_gate_includes_offline_ui_system_contract():
    package = json.loads((FRONTEND / "package.json").read_text())
    workflow = (FRONTEND.parents[1] / ".github/workflows/frontend-build.yml").read_text()

    assert package["scripts"]["test:ui-system"] == (
        "vitest --run __tests__/ui-system.test.ts"
    )
    assert "npm run test:ui-system" in package["scripts"]["test:quality"]
    assert "npm run test:quality" in workflow


def test_runtime_inliner_preserves_adversarial_bundle_text_and_raw_text_boundaries(
    tmp_path,
):
    script = FRONTEND / "scripts/inline-runtime-assets.mjs"
    root = tmp_path / "dist"
    assets = root / "assets"
    assets.mkdir(parents=True)
    js_name = "index-test.js"
    css_name = "index-test.css"
    (root / "index.html").write_text(
        """<!doctype html>
<html><head>
<script type="module" crossorigin src="/assets/index-test.js"></script>
<link rel="stylesheet" crossorigin href="/assets/index-test.css">
</head><body><div id="root"></div></body></html>
""",
        encoding="utf-8",
    )
    (assets / js_name).write_text(
        r'''const values = ["</script>", "<!--", "<!doctype html>", "$'", "$&", "$`"];
// </script> in a comment must remain inside this script.
//# sourceMappingURL=data:text/javascript,/* </script> */
window.__inlineFixture = values;
''',
        encoding="utf-8",
    )
    (assets / css_name).write_text(
        r'''/* </style> in a comment must remain inside this style. */
:root { --inline-fixture: "$'"; }
''',
        encoding="utf-8",
    )

    result = subprocess.run(
        ["node", str(script)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    rendered = (root / "index.html").read_text(encoding="utf-8")
    assert "/assets/index-test.js" not in rendered
    assert "/assets/index-test.css" not in rendered
    assert not assets.exists()
    assert rendered.count("</script>") == 1
    assert rendered.count("</style>") == 1
    assert r"\x3C/script>" in rendered
    assert r"\x3C!--" in rendered
    assert r"\x3C!doctype html>" in rendered
    assert r"\3C/style>" in rendered
    assert "$'" in rendered
    assert "$&" in rendered
    assert "$`" in rendered


def test_runtime_inliner_fails_on_unprocessed_asset_payload(tmp_path):
    script = FRONTEND / "scripts/inline-runtime-assets.mjs"
    root = tmp_path / "dist"
    assets = root / "assets"
    assets.mkdir(parents=True)
    (root / "index.html").write_text("<html></html>", encoding="utf-8")
    (assets / "unexpected.bin").write_bytes(b"unexpected")

    result = subprocess.run(
        ["node", str(script)], cwd=tmp_path, capture_output=True, text=True, check=False
    )

    assert result.returncode != 0
    assert "ENOTEMPTY" in result.stderr


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
    (root / "sbom.json").write_text('{"bomFormat": "CycloneDX", "specVersion": "1.6"}', encoding="utf-8")

    checks = validate_build_metadata(root)

    assert not all(check.passed for check in checks)
    assert any(check.name == "inventory" and not check.passed for check in checks)
    assert any(check.name == "hashes" and not check.passed for check in checks)
    assert any(check.name == "sizes" and not check.passed for check in checks)


def test_python_validator_rejects_missing_manifest_in_release_mode(tmp_path):
    build_binary = FRONTEND.parent / "build-binary"
    sys.path.insert(0, str(build_binary))
    from artifact_validator import validate_build_metadata

    root = tmp_path / "artifact"
    root.mkdir()
    (root / "index.html").write_bytes(b"runtime")

    checks = validate_build_metadata(root, "runtime-admin", "text/html")

    metadata = next(check for check in checks if check.name == "metadata")
    assert metadata.passed is False
    assert metadata.severity == "error"


def test_python_validator_rejects_unsafe_manifest_before_payload_reads(
    monkeypatch, tmp_path
):
    build_binary = FRONTEND.parent / "build-binary"
    sys.path.insert(0, str(build_binary))
    from artifact_validator import validate_build_metadata

    root = tmp_path / "artifact"
    root.mkdir()
    outside = tmp_path / "outside.js"
    outside.write_bytes(b"outside")
    manifest = {
        "schemaVersion": 1,
        "artifact": "runtime-admin",
        "contentType": "text/html",
        "sourceMaps": False,
        "files": [
            {
                "path": "../outside.js",
                "bytes": outside.stat().st_size,
                "sha256": hashlib.sha256(outside.read_bytes()).hexdigest(),
            }
        ],
    }
    (root / "artifact-manifest.json").write_text(json.dumps(manifest))
    (root / "sbom.json").write_text('{"bomFormat": "CycloneDX", "specVersion": "1.6"}')

    reads = []
    original_read_bytes = Path.read_bytes

    def track_read(path):
        reads.append(path)
        return original_read_bytes(path)

    monkeypatch.setattr(Path, "read_bytes", track_read)
    checks = validate_build_metadata(root, "runtime-admin", "text/html")

    assert any(check.name == "inventory" and not check.passed for check in checks)
    assert outside.resolve() not in {path.resolve() for path in reads}


def test_python_validator_preflights_inventory_before_import_scan(
    monkeypatch, tmp_path
):
    build_binary = FRONTEND.parent / "build-binary"
    sys.path.insert(0, str(build_binary))
    import artifact_validator

    root = tmp_path / "artifact"
    root.mkdir()
    (root / "index.js").write_text(
        "import '@sema4ai/components';", encoding="utf-8"
    )
    _write_manifest(
        root,
        "runtime-admin",
        "text/html",
        [{"path": "../outside.js", "bytes": 0, "sha256": "0" * 64}],
    )

    def unexpected_scan(_self, _root):
        pytest.fail("payload import scanning must follow metadata preflight")

    monkeypatch.setattr(
        artifact_validator.tree_shaker.TreeShaker,
        "scan_directory",
        unexpected_scan,
    )

    passed, checks = artifact_validator.validate_artifact(
        root,
        expected_artifact="runtime-admin",
        expected_content_type="text/html",
    )

    assert not passed
    assert any(check.name == "inventory" and not check.passed for check in checks)
    assert any(check.name == "imports" and not check.passed for check in checks)


def test_python_validator_rejects_empty_structural_extras(tmp_path):
    build_binary = FRONTEND.parent / "build-binary"
    sys.path.insert(0, str(build_binary))
    from artifact_validator import validate_build_metadata

    root = tmp_path / "artifact"
    root.mkdir()
    payload = b"runtime"
    (root / "index.html").write_bytes(payload)
    (root / "assets").mkdir()
    _write_manifest(
        root,
        "runtime-admin",
        "text/html",
        [{"path": "index.html", "bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}],
    )

    checks = validate_build_metadata(root, "runtime-admin", "text/html")

    assert any(check.name == "inventory" and not check.passed for check in checks)


def test_javascript_validator_rejects_empty_structural_extras(tmp_path):
    script = FRONTEND / "scripts" / "validate-artifacts.mjs"
    for directory, artifact, content_type in (
        ("dist", "runtime-admin", "text/html"),
        ("dist-canvas", "canvas-mcp-app", "text/html;profile=mcp-app"),
    ):
        root = tmp_path / directory
        root.mkdir()
        payload = f"<html>{content_type}</html>".encode()
        (root / "index.html").write_bytes(payload)
        (root / "assets").mkdir()
        _write_manifest(
            root,
            artifact,
            content_type,
            [{"path": "index.html", "bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}],
        )

    result = subprocess.run(
        ["node", str(script)], cwd=tmp_path, capture_output=True, text=True, check=False
    )

    assert result.returncode != 0
    assert "dist" in (result.stderr + result.stdout)


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
    (root / "sbom.json").write_text('{"bomFormat": "CycloneDX", "specVersion": "1.6"}', encoding="utf-8")

    checks = validate_build_metadata(root)

    assert any(not check.passed for check in checks)


def test_python_validator_treats_nested_metadata_as_payload_inventory(tmp_path):
    build_binary = FRONTEND.parent / "build-binary"
    sys.path.insert(0, str(build_binary))
    from artifact_validator import validate_build_metadata

    root = tmp_path / "artifact"
    nested = root / "nested"
    nested.mkdir(parents=True)
    payload = b"<html>text/html</html>"
    nested_metadata = b"{}"
    (root / "index.html").write_bytes(payload)
    (nested / "artifact-manifest.json").write_bytes(nested_metadata)
    files = [
        {
            "path": path,
            "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
        }
        for path, data in (
            ("index.html", payload),
            ("nested/artifact-manifest.json", nested_metadata),
        )
    ]
    _write_manifest(root, "runtime-admin", "text/html", files)

    checks = validate_build_metadata(root, "runtime-admin", "text/html")

    assert any(check.name == "inventory" and check.passed for check in checks)



@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="requires POSIX special files")
def test_python_validator_rejects_unlisted_non_regular_entries(tmp_path):
    build_binary = FRONTEND.parent / "build-binary"
    sys.path.insert(0, str(build_binary))
    from artifact_validator import validate_build_metadata

    root = tmp_path / "artifact"
    root.mkdir()
    payload = b"<html>text/html</html>"
    (root / "index.html").write_bytes(payload)
    os.mkfifo(root / "payload.pipe")
    _write_manifest(
        root,
        "runtime-admin",
        "text/html",
        [{"path": "index.html", "bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}],
    )

    checks = validate_build_metadata(root, "runtime-admin", "text/html")

    assert any(check.name == "inventory" and not check.passed for check in checks)


def test_javascript_validator_rejects_malformed_sbom(tmp_path):
    script = FRONTEND / "scripts" / "validate-artifacts.mjs"
    for directory, artifact, content_type in (
        ("dist", "runtime-admin", "text/html"),
        ("dist-canvas", "canvas-mcp-app", "text/html;profile=mcp-app"),
    ):
        root = tmp_path / directory
        root.mkdir()
        payload = f"<html>{content_type}</html>".encode()
        (root / "index.html").write_bytes(payload)
        _write_manifest(
            root,
            artifact,
            content_type,
            [{"path": "index.html", "bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}],
        )
    (tmp_path / "dist" / "sbom.json").write_text("{}", encoding="utf-8")

    result = subprocess.run(
        ["node", str(script)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "invalid CycloneDX SBOM" in (result.stderr + result.stdout)


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
    (root / "sbom.json").write_text('{"bomFormat": "CycloneDX", "specVersion": "1.6"}', encoding="utf-8")


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


def test_python_validator_cli_accepts_bound_identity_options(tmp_path):
    build_binary = FRONTEND.parent / "build-binary"
    root = tmp_path / "artifact"
    root.mkdir()
    payload = b"<html>text/html</html>"
    (root / "index.html").write_bytes(payload)
    _write_manifest(
        root,
        "runtime-admin",
        "text/html",
        [
            {
                "path": "index.html",
                "bytes": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
            }
        ],
    )

    result = subprocess.run(
        [
            sys.executable,
            str(build_binary / "artifact_validator.py"),
            "--artifact",
            str(root),
            "--expected-artifact",
            "runtime-admin",
            "--expected-content-type",
            "text/html",
            "--json",
        ],
        cwd=build_binary,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["passed"] is True


def test_python_validator_cli_rejects_bound_file_artifact(tmp_path):
    build_binary = FRONTEND.parent / "build-binary"
    artifact = tmp_path / "artifact.html"
    artifact.write_text("<html>text/html</html>", encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(build_binary / "artifact_validator.py"),
            "--artifact",
            str(artifact),
            "--expected-artifact",
            "runtime-admin",
            "--expected-content-type",
            "text/html",
            "--json",
        ],
        cwd=build_binary,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    report = json.loads(result.stdout)
    assert report["passed"] is False
    assert any(
        check["name"] == "metadata" and not check["passed"]
        for check in report["checks"]
    )


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


def test_javascript_validator_rejects_unsupported_manifest_schema(tmp_path):
    script = FRONTEND / "scripts" / "validate-artifacts.mjs"
    for directory, artifact, content_type in (
        ("dist", "runtime-admin", "text/html"),
        ("dist-canvas", "canvas-mcp-app", "text/html;profile=mcp-app"),
    ):
        root = tmp_path / directory
        root.mkdir()
        payload = f"<html>{content_type}</html>".encode()
        (root / "index.html").write_bytes(payload)
        _write_manifest(
            root,
            artifact,
            content_type,
            [
                {
                    "path": "index.html",
                    "bytes": len(payload),
                    "sha256": hashlib.sha256(payload).hexdigest(),
                }
            ],
        )
    manifest_path = tmp_path / "dist" / "artifact-manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["schemaVersion"] = 2
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    result = subprocess.run(
        ["node", str(script)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "schema" in (result.stderr + result.stdout).lower()


@pytest.mark.parametrize("metadata_name", ["artifact-manifest.json", "sbom.json"])
def test_javascript_validator_rejects_symlinked_metadata_before_parsing(
    tmp_path, metadata_name
):
    script = FRONTEND / "scripts" / "validate-artifacts.mjs"
    for directory, artifact, content_type in (
        ("dist", "runtime-admin", "text/html"),
        ("dist-canvas", "canvas-mcp-app", "text/html;profile=mcp-app"),
    ):
        root = tmp_path / directory
        root.mkdir()
        payload = f"<html>{content_type}</html>".encode()
        (root / "index.html").write_bytes(payload)
        _write_manifest(
            root,
            artifact,
            content_type,
            [{"path": "index.html", "bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}],
        )

    invalid_metadata = tmp_path / "invalid-metadata.json"
    invalid_metadata.write_text("not-json", encoding="utf-8")
    (tmp_path / "dist" / metadata_name).unlink()
    try:
        (tmp_path / "dist" / metadata_name).symlink_to(invalid_metadata)
    except OSError as exc:
        pytest.skip(f"symlink creation unavailable: {exc}")

    result = subprocess.run(
        ["node", str(script)], cwd=tmp_path, capture_output=True, text=True, check=False
    )

    assert result.returncode != 0
    output = (result.stderr + result.stdout).lower()
    assert "symlink" in output
    assert "unexpected token" not in output


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="requires POSIX special files")
@pytest.mark.parametrize("metadata_name", ["artifact-manifest.json", "sbom.json"])
def test_javascript_validator_rejects_fifo_metadata_before_read(
    tmp_path, metadata_name
):
    script = FRONTEND / "scripts" / "validate-artifacts.mjs"
    for directory, artifact, content_type in (
        ("dist", "runtime-admin", "text/html"),
        ("dist-canvas", "canvas-mcp-app", "text/html;profile=mcp-app"),
    ):
        root = tmp_path / directory
        root.mkdir()
        payload = f"<html>{content_type}</html>".encode()
        (root / "index.html").write_bytes(payload)
        _write_manifest(
            root,
            artifact,
            content_type,
            [{"path": "index.html", "bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}],
        )

    (tmp_path / "dist" / metadata_name).unlink()
    os.mkfifo(tmp_path / "dist" / metadata_name)

    try:
        result = subprocess.run(
            ["node", str(script)],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            check=False,
            timeout=3,
        )
    except subprocess.TimeoutExpired as exc:
        pytest.fail(f"validator read non-regular metadata before preflight: {exc}")

    assert result.returncode != 0
    assert "regular" in (result.stderr + result.stdout).lower()


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="requires POSIX special files")
def test_javascript_validator_rejects_non_regular_inventory_entries(tmp_path):
    script = FRONTEND / "scripts" / "validate-artifacts.mjs"
    for directory, artifact, content_type in (
        ("dist", "runtime-admin", "text/html"),
        ("dist-canvas", "canvas-mcp-app", "text/html;profile=mcp-app"),
    ):
        root = tmp_path / directory
        root.mkdir()
        payload = f"<html>{content_type}</html>".encode()
        (root / "index.html").write_bytes(payload)
        special = root / "payload.pipe"
        os.mkfifo(special)
        _write_manifest(
            root,
            artifact,
            content_type,
            [
                {
                    "path": "index.html",
                    "bytes": len(payload),
                    "sha256": hashlib.sha256(payload).hexdigest(),
                },
                {
                    "path": "payload.pipe",
                    "bytes": 0,
                    "sha256": hashlib.sha256(b"").hexdigest(),
                },
            ],
        )

    try:
        result = subprocess.run(
            ["node", str(script)],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            check=False,
            timeout=3,
        )
    except subprocess.TimeoutExpired as exc:
        pytest.fail(f"validator attempted to read a non-regular entry: {exc}")

    assert result.returncode != 0
    assert "regular file" in (result.stderr + result.stdout).lower()


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
