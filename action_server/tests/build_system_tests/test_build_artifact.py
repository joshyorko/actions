from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "build-binary"))

from build_artifact import (  # noqa: E402
    ArtifactType,
    BuildArtifact,
    compute_sha256,
    generate_metadata,
)


def test_compute_sha256_is_deterministic(tmp_path) -> None:
    artifact_file = tmp_path / "frontend-dist.tar.gz"
    artifact_file.write_bytes(b"public frontend bundle")

    expected = hashlib.sha256(b"public frontend bundle").hexdigest()
    assert compute_sha256(artifact_file) == expected
    assert compute_sha256(artifact_file) == expected


def test_build_artifact_records_public_metadata(tmp_path) -> None:
    artifact_file = tmp_path / "frontend-dist.tar.gz"
    artifact_file.write_bytes(b"public frontend bundle")

    artifact = BuildArtifact.create(ArtifactType.FRONTEND, artifact_file)
    metadata = generate_metadata(artifact)

    assert metadata["artifact_type"] == "frontend"
    assert "tier" not in metadata
    assert metadata["sha256"] == artifact.sha256
    assert metadata["size_bytes"] == len(b"public frontend bundle")

    metadata_path = artifact.write_metadata()
    assert json.loads(metadata_path.read_text()) == artifact.to_metadata_json()


def test_build_artifact_requires_existing_sbom(tmp_path) -> None:
    artifact_file = tmp_path / "frontend-dist.tar.gz"
    artifact_file.write_bytes(b"public frontend bundle")

    with pytest.raises(FileNotFoundError):
        BuildArtifact.create(
            ArtifactType.FRONTEND,
            artifact_file,
            sbom_path=tmp_path / "missing-sbom.json",
        )
