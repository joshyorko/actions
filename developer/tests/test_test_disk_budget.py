"""A low-space preflight must stop the caller, not merely print a warning."""
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest


@pytest.fixture
def budget():
    path = Path(__file__).resolve().parents[2] / "scripts/check_test_disk_budget.py"
    spec = importlib.util.spec_from_file_location("test_disk_budget_script", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_low_space_returns_failure_with_preserved_receipt(
    budget, monkeypatch, tmp_path
):
    monkeypatch.setattr(
        budget.shutil, "disk_usage", lambda path: SimpleNamespace(free=99)
    )
    report = tmp_path / "receipt.json"
    assert (
        budget.main(
            [
                "--path",
                str(tmp_path),
                "--required-free-bytes",
                "100",
                "--report",
                str(report),
            ]
        )
        == 2
    )
    assert json.loads(report.read_text())["status"] == "BLOCKED"
    with pytest.raises(FileExistsError):
        budget.main(
            [
                "--path",
                str(tmp_path),
                "--required-free-bytes",
                "100",
                "--report",
                str(report),
            ]
        )


def test_exact_budget_passes_and_nonpositive_budget_refused(
    budget, monkeypatch, tmp_path
):
    monkeypatch.setattr(
        budget.shutil, "disk_usage", lambda path: SimpleNamespace(free=100)
    )
    assert budget.main(["--path", str(tmp_path), "--required-free-bytes", "100"]) == 0
    with pytest.raises(ValueError):
        budget.check(tmp_path, 0)
