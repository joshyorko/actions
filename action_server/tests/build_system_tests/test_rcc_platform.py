"""RCC architecture selection and release gating shared by builds and startup."""

import hashlib
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def platform_module():
    return load_module(
        "rcc_platform_test", ROOT / "src/actions/server/_rcc_platform.py"
    )


@pytest.mark.parametrize("machine", ["aarch64", "arm64", "ARM64"])
def test_linux_arm_routes_to_native_asset(platform_module, machine):
    assert platform_module.rcc_asset_name("linux", machine) == "rcc-linuxarm64"


@pytest.mark.parametrize(
    "system,machine,asset",
    [
        ("linux", "x86_64", "rcc-linux64"),
        ("linux", "AMD64", "rcc-linux64"),
        ("darwin", "arm64", "rcc-macosarm64"),
        ("darwin", "x86_64", "rcc-macos64"),
        ("win32", "AMD64", "rcc-windows64.exe"),
    ],
)
def test_existing_targets(platform_module, system, machine, asset):
    assert platform_module.rcc_asset_name(system, machine) == asset


@pytest.mark.parametrize(
    "system,machine",
    [
        ("linux", "armv7l"),
        ("linux", "ppc64le"),
        ("linux", ""),
        ("freebsd", "x86_64"),
        ("win32", "ARM64"),
    ],
)
def test_unknown_targets_fail_closed(platform_module, system, machine):
    with pytest.raises(RuntimeError, match="Unsupported RCC platform"):
        platform_module.rcc_asset_name(system, machine)


def test_unpublished_arm_release_is_blocked(platform_module):
    with pytest.raises(RuntimeError, match="official.*checksum"):
        platform_module.expected_sha256("18.19.8", "rcc-linuxarm64")


def test_arm_checksum_and_elf_required(platform_module, tmp_path, monkeypatch):
    binary = tmp_path / "rcc"
    body = b"\x7fELF\x02\x01" + bytes(12) + b"\xb7\x00" + bytes(12)
    binary.write_bytes(body)
    digest = hashlib.sha256(body).hexdigest()
    monkeypatch.setattr(platform_module, "LINUX_ARM64_RELEASE_SHA256", {"test": digest})
    platform_module.verify_rcc(binary, "test", "rcc-linuxarm64")
    binary.write_bytes(body + b"tampered")
    with pytest.raises(RuntimeError, match="checksum"):
        platform_module.verify_rcc(binary, "test", "rcc-linuxarm64")
    wrong_arch = body[:18] + b"\x3e\x00" + body[20:]
    binary.write_bytes(wrong_arch)
    monkeypatch.setattr(
        platform_module,
        "LINUX_ARM64_RELEASE_SHA256",
        {"test": hashlib.sha256(wrong_arch).hexdigest()},
    )
    with pytest.raises(RuntimeError, match="AArch64"):
        platform_module.verify_rcc(binary, "test", "rcc-linuxarm64")


def test_build_hook_blocks_arm_before_download(monkeypatch):
    build = load_module("rcc_build_test", ROOT / "build.py")
    monkeypatch.setattr(build.sys, "platform", "linux")
    monkeypatch.setattr(build.platform, "machine", lambda: "aarch64")
    monkeypatch.setattr(
        build,
        "_download_with_resume",
        lambda *args: pytest.fail("network before release approval"),
    )
    with pytest.raises(RuntimeError, match="official.*checksum"):
        build._download_rcc()


def test_runtime_blocks_cached_x64_on_arm(tmp_path, monkeypatch):
    from actions.server import _download_rcc

    cached = tmp_path / "rcc"
    cached.write_bytes(b"existing x64 binary")
    monkeypatch.setattr(_download_rcc.sys, "platform", "linux")
    monkeypatch.setattr(_download_rcc.platform, "machine", lambda: "aarch64")
    with pytest.raises(RuntimeError, match="official.*checksum"):
        _download_rcc.download_rcc(str(cached))
    assert cached.read_bytes() == b"existing x64 binary"


@pytest.mark.parametrize("valid", [True, False])
def test_arm_download_verifies_before_replace(tmp_path, monkeypatch, valid):
    from types import SimpleNamespace

    import actions_http

    from actions.server import _download_rcc, _rcc_platform

    body = b"\x7fELF\x02\x01" + bytes(12) + b"\xb7\x00" + bytes(12)
    monkeypatch.setattr(
        _rcc_platform,
        "LINUX_ARM64_RELEASE_SHA256",
        {_download_rcc.RCC_VERSION: hashlib.sha256(body).hexdigest()},
    )
    monkeypatch.setattr(_download_rcc.sys, "platform", "linux")
    monkeypatch.setattr(_download_rcc.platform, "machine", lambda: "aarch64")
    target = tmp_path / "rcc"
    target.write_bytes(b"previous")
    urls = []

    def download(url, path, **kwargs):
        urls.append(url)
        path.write_bytes(body if valid else b"bad checksum")
        return SimpleNamespace(status=None)

    monkeypatch.setattr(actions_http, "download_with_resume", download)
    if valid:
        assert _download_rcc.download_rcc(str(target), force=True) == target
        assert target.read_bytes() == body
        assert _download_rcc.download_rcc(str(target)) == target
    else:
        with pytest.raises(RuntimeError, match="checksum"):
            _download_rcc.download_rcc(str(target), force=True)
        assert target.read_bytes() == b"previous"
    assert len(urls) == 1
    assert urls[0].endswith("/v18.19.8/rcc-linuxarm64")
    assert not target.with_name("rcc.download").exists()


def test_candidate_harness_rejects_x64(tmp_path):
    import platform
    import subprocess
    import sys

    if platform.machine().lower() in ("aarch64", "arm64"):
        pytest.skip("negative host gate requires a non-ARM64 host")
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/verify_linux_arm64_candidate.py"),
            "--rcc",
            str(tmp_path / "unused"),
            "--rcc-sha256",
            "unused",
            "--output",
            str(tmp_path / "receipt.json"),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2
    assert "native Linux ARM64 required" in result.stderr
    assert not (tmp_path / "receipt.json").exists()
