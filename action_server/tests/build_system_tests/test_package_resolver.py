import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[2] / "build-binary"))

from package_resolver import validate_frontend_contract


def test_validates_canonical_frontend_contract(tmp_path):
    (tmp_path / "package.json").write_text(json.dumps({"name": "actions"}))
    (tmp_path / "package-lock.json").write_text("{}")

    validate_frontend_contract(tmp_path)


def test_rejects_missing_lock(tmp_path):
    (tmp_path / "package.json").write_text(json.dumps({"name": "actions"}))

    with pytest.raises(ValueError, match="package-lock"):
        validate_frontend_contract(tmp_path)
