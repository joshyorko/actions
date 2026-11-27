"""Dependency-free RCC platform contract shared by wheel builds and startup."""

import hashlib
from pathlib import Path

# Add only an official joshyorko/rcc release digest after checking its published
# checksum and trust metadata. Candidate builds must never populate this table.
LINUX_ARM64_RELEASE_SHA256: dict[str, str] = {
    "18.19.12": "e161f9d750776c376ef19ba15676b166447bc12096d208de2ecbbe51899cb1d2",
}


def rcc_asset_name(system: str, machine: str) -> str:
    machine = machine.lower()
    assets = {
        ("linux", "x86_64"): "rcc-linux64",
        ("linux", "amd64"): "rcc-linux64",
        ("linux", "aarch64"): "rcc-linuxarm64",
        ("linux", "arm64"): "rcc-linuxarm64",
        ("darwin", "arm64"): "rcc-macosarm64",
        ("darwin", "aarch64"): "rcc-macosarm64",
        ("darwin", "x86_64"): "rcc-macos64",
        ("win32", "amd64"): "rcc-windows64.exe",
        ("win32", "x86_64"): "rcc-windows64.exe",
    }
    try:
        return assets[system, machine]
    except KeyError:
        raise RuntimeError(f"Unsupported RCC platform: {system}/{machine}") from None


def expected_sha256(version: str, asset: str) -> str | None:
    if asset != "rcc-linuxarm64":
        return None
    digest = LINUX_ARM64_RELEASE_SHA256.get(version)
    if digest is None:
        raise RuntimeError(
            f"RCC {version} Linux ARM64 requires an official release checksum "
            "and verified trust metadata; candidate builds are test-only."
        )
    return digest


def verify_rcc(path: Path, version: str, asset: str) -> None:
    digest = expected_sha256(version, asset)
    if digest is None:
        return
    with path.open("rb") as stream:
        header = stream.read(20)
        stream.seek(0)
        actual = hashlib.file_digest(stream, "sha256").hexdigest()
    if actual != digest:
        raise RuntimeError(f"RCC checksum mismatch for {asset}")
    if header[:6] != b"\x7fELF\x02\x01" or header[18:20] != b"\xb7\x00":
        raise RuntimeError("RCC Linux ARM64 must be a little-endian AArch64 ELF64")
