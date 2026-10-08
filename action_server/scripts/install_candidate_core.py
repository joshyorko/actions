"""Install a built Core wheel into PR-only cibuildwheel test environments."""

import hashlib
import subprocess
import sys
import zipfile
from email.parser import BytesParser
from pathlib import Path


def select_candidate(directory: Path) -> Path:
    wheels = sorted(directory.glob("*.whl"))
    if len(wheels) != 1:
        raise ValueError("Expected exactly one candidate Core wheel")
    wheel = wheels[0]
    with zipfile.ZipFile(wheel) as archive:
        paths = [
            name for name in archive.namelist() if name.endswith(".dist-info/METADATA")
        ]
        if len(paths) != 1:
            raise ValueError("Expected exactly one Core wheel METADATA")
        metadata = BytesParser().parsebytes(archive.read(paths[0]))
        if metadata["Name"] != "actions-core" or not metadata["Version"]:
            raise ValueError("Candidate is not an identified Core distribution")
    return wheel


if __name__ == "__main__":
    wheel = select_candidate(Path(sys.argv[1]))
    print(
        f"Candidate Core: {wheel.name} sha256:{hashlib.sha256(wheel.read_bytes()).hexdigest()}",
        flush=True,
    )
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "--no-deps", str(wheel)],
        check=True,
        timeout=120,
    )
