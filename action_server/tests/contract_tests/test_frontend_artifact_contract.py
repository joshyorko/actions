import hashlib
import json
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
    assert "text/html;profile=mcp-app" in validator


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
        "vitest --run __tests__/topology/frontend-topology.test.ts"
    )


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
