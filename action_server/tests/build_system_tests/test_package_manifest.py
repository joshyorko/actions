import json
import sys
from pathlib import Path

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
