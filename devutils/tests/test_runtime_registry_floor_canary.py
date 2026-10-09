import importlib.util
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[2]
SCRIPT = ROOT / "action_server/scripts/verify_published_runtime_floor.py"
spec = importlib.util.spec_from_file_location("runtime_registry_floor", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def _wheel(directory, name, version, filename=None):
    path = directory / (
        filename or f"actions_runtime-{version}-cp312-cp312-manylinux_2_17_x86_64.whl"
    )
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(
            f"actions_runtime-{version}.dist-info/METADATA",
            f"Metadata-Version: 2.1\nName: {name}\nVersion: {version}\n",
        )
    return path


def test_selects_one_cp312_runtime_wheel(tmp_path):
    expected = _wheel(tmp_path, "actions-runtime", "1.0.3")
    _wheel(
        tmp_path,
        "actions-runtime",
        "1.0.3",
        "actions_runtime-1.0.3-cp313-cp313-manylinux_2_17_x86_64.whl",
    )
    assert module.select_runtime_wheel(tmp_path) == expected


def test_rejects_wrong_runtime_version(tmp_path):
    _wheel(tmp_path, "actions-runtime", "1.0.2")
    with pytest.raises(ValueError, match="Unexpected Runtime version"):
        module.select_runtime_wheel(tmp_path)


def test_rejects_non_runtime_distribution(tmp_path):
    _wheel(tmp_path, "actions-core", "1.0.3")
    with pytest.raises(ValueError, match="Unexpected distribution"):
        module.select_runtime_wheel(tmp_path)


def test_rejects_ambiguous_cp312_wheel_inventory(tmp_path):
    _wheel(tmp_path, "actions-runtime", "1.0.3")
    _wheel(
        tmp_path,
        "actions-runtime",
        "1.0.3",
        "actions_runtime-1.0.3-cp312-abi3-manylinux_2_17_x86_64.whl",
    )
    with pytest.raises(ValueError, match="exactly one cp312"):
        module.select_runtime_wheel(tmp_path)
