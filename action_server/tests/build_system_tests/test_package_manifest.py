import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[2] / "build-binary"))

from package_manifest import PackageManifest


def test_loads_and_validates_canonical_manifest(tmp_path):
    (tmp_path / "package.json").write_text(json.dumps({"name": "actions", "dependencies": {"react": "^18.0.0"}}))
    (tmp_path / "package-lock.json").write_text(json.dumps({"packages": {"": {"name": "actions"}}}))

    manifest = PackageManifest.load(tmp_path)

    assert manifest.file_path == tmp_path / "package.json"
    assert manifest.validate().passed


def test_rejects_private_product_dependency(tmp_path):
    (tmp_path / "package.json").write_text(json.dumps({"dependencies": {"@sema4ai/theme": "^1.0.0"}}))
    (tmp_path / "package-lock.json").write_text("{}")

    assert not PackageManifest.load(tmp_path).validate().passed


@pytest.mark.parametrize("package_name", ["@codemirror/view", "@radix-ui/react-dialog"])
def test_allows_public_scoped_dependency(tmp_path, package_name):
    (tmp_path / "package.json").write_text(json.dumps({"dependencies": {package_name: "^1.0.0"}}))
    (tmp_path / "package-lock.json").write_text("{}")

    assert PackageManifest.load(tmp_path).validate().passed


@pytest.mark.parametrize(
    "dependency",
    [
        {"@sema4ai/theme": "^1.0.0"},
        {"actions-runtime-components": "file:./vendored/components"},
        {"actions-runtime-icons": "https://npm.pkg.github.com/actions-runtime-icons.tgz"},
    ],
)
def test_rejects_prohibited_product_dependency_or_registry(tmp_path, dependency):
    (tmp_path / "package.json").write_text(json.dumps({"dependencies": dependency}))
    (tmp_path / "package-lock.json").write_text("{}")

    result = PackageManifest.load(tmp_path).validate()

    assert not result.passed
