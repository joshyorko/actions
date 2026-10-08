"""Measure pytest-cov line coverage across the portable Python package suites."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PACKAGES = ("actions", "actions-http-helper", "devutils", "work-items", "action_server")
TEST_ARGUMENTS = {
    "actions": ["tests"],
    "actions-http-helper": ["tests"],
    "devutils": ["tests"],
    "work-items": ["tests", "-m", "not persistent_backend_service"],
    "action_server": ["tests", "-m", "not integration_test", "-rfE", "-n", "auto"],
}
THRESHOLDS = ROOT / ".coverage-thresholds.json"


def source_files(package: str) -> list[Path]:
    """Inventory every maintained Python module under a package's source root."""
    source_root = ROOT / package / "src"
    files = sorted(path.resolve() for path in source_root.rglob("*.py"))
    if not files:
        raise ValueError(f"no Python sources found under {source_root}")
    return files


def inventory_digest(sources: list[Path]) -> str:
    """Fingerprint the exact maintained source used by a measured baseline."""
    digest = hashlib.sha256()
    for source in sorted(sources):
        digest.update(source.relative_to(ROOT).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(source.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def summarize_reports(reports: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Sum pytest-cov's real per-package source statements and covered lines."""
    total_statements = 0
    covered_statements = 0
    missing_source: dict[str, list[str]] = {}
    for package in PACKAGES:
        report = reports.get(package)
        if report is None:
            missing_source[package] = ["package coverage report is missing"]
            continue
        files = report.get("files")
        totals = report.get("totals")
        if not isinstance(files, dict) or not isinstance(totals, dict):
            raise ValueError(f"{package} coverage JSON has no files/totals objects")
        expected = set(source_files(package))
        observed: dict[Path, dict[str, Any]] = {}
        for name, details in files.items():
            path = Path(name)
            if not path.is_absolute():
                path = (ROOT / package / path).resolve()
            else:
                path = path.resolve()
            if path not in expected:
                raise ValueError(
                    f"{package} coverage report includes non-source file: {name}"
                )
            if path in observed:
                raise ValueError(f"{package} coverage report repeats source file: {name}")
            if not isinstance(details, dict) or not isinstance(details.get("summary"), dict):
                raise ValueError(f"{package} coverage summary is invalid for {name}")
            observed[path] = details["summary"]
        absent = expected - set(observed)
        if absent:
            missing_source[package] = [path.relative_to(ROOT).as_posix() for path in sorted(absent)]
        package_statements = 0
        package_covered = 0
        for details in observed.values():
            file_statements = int(details.get("num_statements", -1))
            file_covered = int(details.get("covered_lines", -1))
            if file_statements < 0 or file_covered < 0 or file_covered > file_statements:
                raise ValueError(f"{package} coverage file counts are invalid")
            package_statements += file_statements
            package_covered += file_covered
        if package_statements != int(totals.get("num_statements", -1)):
            raise ValueError(f"{package} coverage statement total does not match source files")
        if package_covered != int(totals.get("covered_lines", -1)):
            raise ValueError(f"{package} covered line total does not match source files")
        if package_statements <= 0:
            raise ValueError(f"{package} coverage report has no executable statements")
        if package_covered > package_statements:
            raise ValueError(f"{package} covered line count exceeds its statement count")
        total_statements += package_statements
        covered_statements += package_covered
    if total_statements <= 0:
        raise ValueError("no Python source statements were measured")
    percent = covered_statements * 100.0 / total_statements
    return {
        "statement_count": total_statements,
        "covered_statements": covered_statements,
        "statement_percent": round(percent, 4),
        "missing_source_files": missing_source,
    }


def meets_floor(measured: float, floor: float) -> bool:
    return measured >= floor


def _output_dir() -> Path:
    return Path(
        os.environ.get(
            "COVERAGE_OUTPUT_DIR",
            str(Path(tempfile.gettempdir()) / "actions-coverage-gate"),
        )
    )


def _package_command(package: str, report_path: Path) -> list[str]:
    source_root = (ROOT / package / "src").resolve()
    return [
        "poetry",
        "run",
        "pytest",
        *TEST_ARGUMENTS[package],
        f"--cov-config={ROOT / '.coveragerc'}",
        f"--cov={source_root}",
        f"--cov-report=json:{report_path}",
    ]


def _suite_environment(package: str) -> dict[str, str]:
    env = os.environ.copy()
    if package == "action_server":
        runtime_python = env.get("ACTIONS_RUNTIME_TEST_PYTHON")
        if not runtime_python or not Path(runtime_python).is_file():
            raise FileNotFoundError(
                "RCC must provide ACTIONS_RUNTIME_TEST_PYTHON for the Action "
                "Server wheel contract"
            )
    return env


def _orchestrate(record_baseline: bool) -> int:
    output_dir = _output_dir()
    package_dir = output_dir / "packages"
    package_dir.mkdir(parents=True, exist_ok=True)
    reports: dict[str, dict[str, Any]] = {}
    suite_states: dict[str, str] = {}
    suite_exit_codes: dict[str, int | None] = {}

    for package in PACKAGES:
        report_path = package_dir / f"{package}.json"
        report_path.unlink(missing_ok=True)
        command = _package_command(package, report_path)
        print(f"+ {' '.join(command)} (in {ROOT / package})", flush=True)
        try:
            process = subprocess.run(
                command,
                cwd=ROOT / package,
                env=_suite_environment(package),
                check=False,
            )
            suite_exit_codes[package] = process.returncode
        except OSError as error:
            suite_exit_codes[package] = None
            print(f"Unable to start {package} coverage suite: {error}", file=sys.stderr)
        if suite_exit_codes[package] == 0 and report_path.is_file():
            suite_states[package] = "PASS"
            reports[package] = json.loads(report_path.read_text(encoding="utf-8"))
        elif suite_exit_codes[package] is None:
            suite_states[package] = "BLOCKED"
        else:
            suite_states[package] = "FAIL"

    failed = [package for package, state in suite_states.items() if state != "PASS"]
    report: dict[str, Any] | None = None
    floor: float | None = None
    baseline_written = False
    try:
        report = summarize_reports(reports)
    except (TypeError, ValueError, json.JSONDecodeError) as error:
        failed.append(f"coverage report invalid: {error}")

    if report is not None and not report["missing_source_files"]:
        if record_baseline and not failed:
            floor = math.floor(float(report["statement_percent"]) * 100) / 100
            sources = [source for package in PACKAGES for source in source_files(package)]
            THRESHOLDS.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "measurement": "pytest-cov line coverage over Python source statements",
                        "packages": list(PACKAGES),
                        "suite_exclusions": {
                            "work-items": "persistent_backend_service",
                            "action_server": "integration_test",
                        },
                        "baseline_source_commit": subprocess.check_output(
                            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
                        ).strip(),
                        "baseline_source_sha256": inventory_digest(sources),
                        "baseline_statements": report["statement_count"],
                        "baseline_covered_statements": report["covered_statements"],
                        "minimum_statement_percent": floor,
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            baseline_written = True
        elif not record_baseline:
            if not THRESHOLDS.is_file():
                failed.append("missing .coverage-thresholds.json")
            else:
                thresholds = json.loads(THRESHOLDS.read_text(encoding="utf-8"))
                floor = float(thresholds["minimum_statement_percent"])
                if not meets_floor(float(report["statement_percent"]), floor):
                    failed.append("coverage below measured floor")
    elif report is not None:
        failed.append("source inventory is incomplete")

    payload = {
        "state": "PASS" if not failed else "FAIL",
        "suite_states": suite_states,
        "suite_exit_codes": suite_exit_codes,
        "failed_gates": failed,
        "minimum_statement_percent": floor,
        "measured": report,
        "baseline_written": baseline_written,
        "subprocess_coverage": "Python launched by tests outside pytest-cov's worker management is not measured.",
    }
    summary_path = output_dir / "coverage-summary.json"
    summary_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))
    print(f"Coverage receipt: {summary_path}")
    return 1 if failed else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--record-baseline", action="store_true")
    args = parser.parse_args()
    return _orchestrate(args.record_baseline)


if __name__ == "__main__":
    raise SystemExit(main())
