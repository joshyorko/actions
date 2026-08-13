"""Regression coverage for the build-binary top-level import contract."""

import subprocess
import sys
from pathlib import Path


def test_artifact_validator_imports_from_build_binary_directory():
    """The task runner imports build-binary helpers as top-level modules."""
    build_binary = Path(__file__).parents[2] / "build-binary"

    result = subprocess.run(
        [sys.executable, "-c", "import artifact_validator"],
        cwd=build_binary,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
