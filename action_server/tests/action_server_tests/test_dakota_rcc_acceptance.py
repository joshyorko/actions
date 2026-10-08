import os
import subprocess
import sys
from pathlib import Path

import pytest


SCRIPT = Path(__file__).parents[2] / "scripts" / "verify_dakota_rcc_acceptance.py"


def test_dakota_acceptance_harness_describes_candidate_wheel_proof():
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--help"],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )

    assert result.returncode == 0, result.stderr
    assert "candidate-wheel" in result.stdout
    assert "RCC Environment Artifact" in result.stdout


@pytest.mark.integration_test
@pytest.mark.real_rcc
def test_dakota_local_rcc_action_over_authenticated_http():
    if os.environ.get("ACTIONS_REAL_RCC_ACCEPTANCE") != "1":
        pytest.skip("set ACTIONS_REAL_RCC_ACCEPTANCE=1 for the live local proof")

    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--mode", "candidate-wheel"],
        check=False,
        capture_output=True,
        text=True,
        timeout=1200,
        env=os.environ.copy(),
    )

    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    assert '"status": "passed"' in result.stdout
    assert '"runtime_mode": "candidate-wheel"' in result.stdout
