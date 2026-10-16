"""Qualification-only orchestration; never publish or touch the protected owner run."""
import json
import os
from pathlib import Path

import runtime_release_qualification_support as support

PROTECTED_OWNER = 38951733318
REPORT = Path("recovery-qualification-report.json")


def main():
    support.REPORT = REPORT
    request = json.loads(
        Path("scripts/runtime-release-recovery-request.json").read_text()
    )
    support.require(
        request["operation"] == "prepare-disposable",
        "unsupported qualification operation",
    )
    support.require(
        request["purpose"] == "disposable-recovery-rehearsal",
        "explicit disposable purpose required",
    )
    report = {
        "status": "RUNNING",
        "purpose": request["purpose"],
        "dispatches": [],
        "runs": [],
        "bundles": [],
        "publication_performed": False,
        "protected_owner_preparation": PROTECTED_OWNER,
        "creation_controller_run_id": int(os.environ["GITHUB_RUN_ID"]),
        "creation_controller_sha": os.environ["GITHUB_SHA"],
    }
    support.snapshot(report)
    try:
        support.publication_absent(request["version"])
        run_id = support.dispatch(
            report,
            "disposable-recovery-preparation",
            "prepare",
            request["source_sha"],
            request["qualification_sha"],
            request["version"],
        )
        support.require(
            run_id != PROTECTED_OWNER,
            "protected owner run cannot be a disposable preparation",
        )
        run = support.wait_run(run_id)
        support.result(report, "disposable-recovery-preparation", run)
        support.require(run["conclusion"] == "success", "disposable preparation failed")
        support.bundle(
            report,
            "disposable",
            run_id,
            request["source_sha"],
            request["qualification_sha"],
            request["version"],
        )
        report["disposable_preparation_run_id"] = run_id
        report["status"] = "PASS"
    except Exception as error:
        report.update(
            status="FAILED", error_type=type(error).__name__, error=str(error)
        )
        raise
    finally:
        support.snapshot(report)


if __name__ == "__main__":
    main()
