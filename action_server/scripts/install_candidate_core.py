"""Install a built Core wheel into PR-only cibuildwheel test environments."""

import hashlib
import subprocess
import sys
import zipfile
from email.parser import BytesParser
from pathlib import Path


def select_candidate(directory: Path, distribution: str = "actions-core") -> Path:
    label = "Core" if distribution == "actions-core" else "HTTP Helper"
    wheels = sorted(directory.glob("*.whl"))
    if len(wheels) != 1:
        raise ValueError(f"Expected exactly one candidate {label} wheel")
    wheel = wheels[0]
    with zipfile.ZipFile(wheel) as archive:
        paths = [
            name for name in archive.namelist() if name.endswith(".dist-info/METADATA")
        ]
        if len(paths) != 1:
            raise ValueError(f"Expected exactly one {label} wheel METADATA")
        metadata = BytesParser().parsebytes(archive.read(paths[0]))
        if metadata["Name"] != distribution or not metadata["Version"]:
            raise ValueError(f"Candidate is not an identified {label} distribution")
    return wheel


if __name__ == "__main__":
    wheels = [select_candidate(Path(sys.argv[1]))]
    if len(sys.argv) > 2:
        wheels.insert(0, select_candidate(Path(sys.argv[2]), "actions-http-helper"))
    for wheel in wheels:
        print(
            f"Candidate: {wheel.name} sha256:{hashlib.sha256(wheel.read_bytes()).hexdigest()}",
            flush=True,
        )
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--no-deps",
            *(str(wheel) for wheel in wheels),
        ],
        check=True,
        timeout=120,
    )
