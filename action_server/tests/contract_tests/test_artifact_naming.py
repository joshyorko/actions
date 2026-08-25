from __future__ import annotations

import sys
from pathlib import Path

BUILD_BINARY = Path(__file__).resolve().parents[2] / "build-binary"
sys.path.insert(0, str(BUILD_BINARY))

from build_artifact import (  # noqa: E402
    ArtifactType,
    extract_commit_from_name,
    extract_platform_from_name,
    generate_artifact_name,
    validate_artifact_name,
)


def test_public_frontend_artifact_name() -> None:
    name = generate_artifact_name(ArtifactType.FRONTEND)

    assert name == "frontend-dist.tar.gz"
    assert validate_artifact_name(name, ArtifactType.FRONTEND)


def test_public_executable_artifact_name() -> None:
    name = generate_artifact_name(
        ArtifactType.EXECUTABLE, platform="linux", git_commit="a1b2c3d"
    )

    assert name == "action-server-linux-a1b2c3d.zip"
    assert validate_artifact_name(name, ArtifactType.EXECUTABLE)
    assert extract_platform_from_name(name) == "linux"
    assert extract_commit_from_name(name) == "a1b2c3d"


def test_removed_tier_names_are_rejected() -> None:
    assert not validate_artifact_name(
        "frontend-dist-enterprise.tar.gz", ArtifactType.FRONTEND
    )
    assert not validate_artifact_name(
        "action-server-community-linux-a1b2c3d.zip", ArtifactType.EXECUTABLE
    )
