from __future__ import annotations

from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).parents[1]))
import coverage_gate  # noqa: E402


def test_aggregate_uses_every_package_report_and_exact_source_inventory(
    tmp_path: Path, monkeypatch
) -> None:
    source_files = {package: tmp_path / f"{package}.py" for package in coverage_gate.PACKAGES}
    for source in source_files.values():
        source.write_text("value = 1\n")
    monkeypatch.setattr(
        coverage_gate,
        "source_files",
        lambda package: [source_files[package]],
    )
    reports = {
        package: {
            "files": {
                str(source_files[package]): {
                    "summary": {"num_statements": 10, "covered_lines": 8}
                }
            },
            "totals": {"num_statements": 10, "covered_lines": 8},
        }
        for package in coverage_gate.PACKAGES
    }

    summary = coverage_gate.summarize_reports(reports)

    assert summary == {
        "statement_count": 50,
        "covered_statements": 40,
        "statement_percent": 80.0,
        "missing_source_files": {},
    }


def test_missing_package_report_is_visible_as_incomplete_source_coverage(
    tmp_path: Path, monkeypatch
) -> None:
    source_files = {package: tmp_path / f"{package}.py" for package in coverage_gate.PACKAGES}
    for source in source_files.values():
        source.write_text("value = 1\n")
    monkeypatch.setattr(
        coverage_gate,
        "source_files",
        lambda package: [source_files[package]],
    )
    reports = {
        package: {
            "files": {
                str(source_files[package]): {
                    "summary": {"num_statements": 1, "covered_lines": 1}
                }
            },
            "totals": {"num_statements": 1, "covered_lines": 1},
        }
        for package in coverage_gate.PACKAGES[:-1]
    }

    summary = coverage_gate.summarize_reports(reports)

    assert summary["missing_source_files"]["action_server"] == [
        "package coverage report is missing"
    ]


def test_unexpected_file_cannot_inflate_measured_coverage(
    tmp_path: Path, monkeypatch
) -> None:
    source_files = {package: tmp_path / f"{package}.py" for package in coverage_gate.PACKAGES}
    for source in source_files.values():
        source.write_text("value = 1\n")
    monkeypatch.setattr(
        coverage_gate,
        "source_files",
        lambda package: [source_files[package]],
    )
    reports = {
        package: {
            "files": {
                str(source_files[package]): {
                    "summary": {"num_statements": 1, "covered_lines": 1}
                }
            },
            "totals": {"num_statements": 1, "covered_lines": 1},
        }
        for package in coverage_gate.PACKAGES
    }
    inflated_file = tmp_path / "artificially-covered.py"
    reports["actions"]["files"][str(inflated_file)] = {
        "summary": {"num_statements": 1000, "covered_lines": 1000}
    }
    reports["actions"]["totals"] = {
        "num_statements": 1001,
        "covered_lines": 1001,
    }

    with pytest.raises(ValueError, match="non-source file"):
        coverage_gate.summarize_reports(reports)


def test_coverage_floor_rejects_a_measured_drop() -> None:
    assert coverage_gate.meets_floor(79.99, 80.0) is False
    assert coverage_gate.meets_floor(80.0, 80.0) is True


def test_action_server_measurement_keeps_full_suite_flags_and_cov_plugin() -> None:
    command = coverage_gate._package_command("action_server", Path("report.json"))

    assert "-m" in command
    assert "not integration_test" in command
    assert "--force-regen" not in command
    assert command[command.index("-n") + 1] == "auto"
    assert any(argument.startswith("--cov=") for argument in command)
    assert any(argument.startswith("--cov-config=") for argument in command)
    assert "--cov-report=json:report.json" in command


def test_action_server_uses_the_rcc_created_python_for_wheel_tests(
    tmp_path: Path, monkeypatch
) -> None:
    rcc_python = tmp_path / "rcc" / "bin" / "python"
    rcc_python.parent.mkdir(parents=True)
    rcc_python.touch()
    monkeypatch.setenv("ACTIONS_RUNTIME_TEST_PYTHON", str(rcc_python))

    env = coverage_gate._suite_environment("action_server")

    assert env["ACTIONS_RUNTIME_TEST_PYTHON"] == str(rcc_python)


def test_source_inventory_digest_changes_when_maintained_code_changes(
    tmp_path: Path, monkeypatch
) -> None:
    source = tmp_path / "sample.py"
    source.write_text("value = 1\n")
    monkeypatch.setattr(coverage_gate, "ROOT", tmp_path)
    before = coverage_gate.inventory_digest([source])
    source.write_text("value = 2\n")

    assert coverage_gate.inventory_digest([source]) != before
