"""Boundary controls for the read-only resource source, not workload admission."""

import importlib.util
import os
import sys
from pathlib import Path

import pytest


def _module():
    specification = importlib.util.find_spec("devutils.native_resources")
    assert specification is not None, "MISSING_ADOPTED_RESOURCE_SOURCE"
    from devutils import native_resources

    return native_resources


@pytest.mark.parametrize("raw", [b"", b"-1\n", b"1 2\n", b"1", b"max\n", b"secret\n"])
def test_counter_failure_never_becomes_available_capacity(raw):
    module = _module()
    with pytest.raises(module.ResourceUnavailable, match="^COUNTER_SCHEMA$"):
        module.parse_counter(raw)


def test_unlimited_child_is_distinct_from_a_zero_limit():
    module = _module()
    assert module.parse_counter(b"max\n", allow_max=True) is None
    assert module.parse_counter(b"0\n", allow_max=True) == 0


@pytest.mark.skipif(sys.platform != "linux", reason="Linux resource source")
@pytest.mark.parametrize("member", [("..",), (".",), ("",), ("x/y",)])
def test_untrusted_member_route_is_rejected_before_open(monkeypatch, member):
    module = _module()

    def unexpected_open(*args, **kwargs):
        pytest.fail("invalid member route reached descriptor creation")

    monkeypatch.setattr(module.os, "open", unexpected_open)
    with pytest.raises(module.ResourceUnavailable, match="^SOURCE_PATH$"):
        module.MemorySource(Path("/sys/fs/cgroup"), member)


def test_non_linux_source_fails_clearly_before_open(monkeypatch):
    module = _module()
    monkeypatch.setattr(module.sys, "platform", "win32")
    with pytest.raises(module.ResourceUnavailable, match="^UNSUPPORTED_PLATFORM$"):
        module.MemorySource(Path("/sys/fs/cgroup"), ())


@pytest.mark.skipif(sys.platform != "linux", reason="Linux resource source")
def test_regular_fixture_directory_is_not_a_cgroup_source(tmp_path):
    module = _module()
    with pytest.raises(module.ResourceUnavailable, match="^CGROUP2_MOUNT$"):
        module.MemorySource(tmp_path, ())


@pytest.mark.skipif(sys.platform != "linux", reason="Linux cgroup witness")
def test_real_witness_uses_ancestor_limit_without_namespace_root_rewrite():
    module = _module()
    mount = Path("/sys/fs/cgroup")
    candidates = [(), ("init",)]
    member = None
    for candidate in candidates:
        try:
            pids = (mount.joinpath(*candidate) / "cgroup.procs").read_bytes().splitlines()
        except OSError:
            continue
        if str(os.getpid()).encode() in pids:
            member = candidate
            break
    if member is None:
        pytest.skip("no local root/init self witness; actual native source remains unavailable")
    with module.MemorySource(mount, member) as source:
        first = source.read()
        second = source.read()
        assert first.observer_pid == second.observer_pid == os.getpid()
        assert first.scope == second.scope == "shared_visible_ancestors"
        assert first.reserved_capacity is False
        assert first.entire_effective_limit_known is False
        assert [(c.device, c.inode) for c in first.constraints] == [
            (c.device, c.inode) for c in second.constraints
        ]
        assert any(c.limit is not None for c in first.constraints)
        assert first.shared_margin >= 0
    with pytest.raises(module.ResourceUnavailable, match="^SOURCE_LIFETIME$"):
        source.read()
