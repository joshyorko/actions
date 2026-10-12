"""Read a witnessed cgroup resource source without admitting a workload.

The mount's namespace-relative root is deliberately opaque. Membership and
the ancestor route are proved through descriptors, rather than path rewriting.
"""

from __future__ import annotations

import os
import stat
import sys
import time
from dataclasses import dataclass
from pathlib import Path


class ResourceUnavailable(RuntimeError):
    """A fixed reason for unavailable evidence; never a clean capacity result."""


@dataclass(frozen=True)
class MemoryConstraint:
    device: int
    inode: int
    current: int
    limit: int | None


@dataclass(frozen=True)
class MemoryObservation:
    observer_pid: int
    observed_ns: int
    constraints: tuple[MemoryConstraint, ...]
    shared_margin: int
    scope: str = "shared_visible_ancestors"
    reserved_capacity: bool = False
    entire_effective_limit_known: bool = False


def parse_counter(raw: bytes, *, allow_max: bool = False) -> int | None:
    if allow_max and raw == b"max\n":
        return None
    if not raw.endswith(b"\n") or not raw[:-1].isdigit():
        raise ResourceUnavailable("COUNTER_SCHEMA")
    return int(raw[:-1])


def _read(fd: int, maximum: int = 65536) -> bytes:
    os.lseek(fd, 0, os.SEEK_SET)
    pieces = []
    size = 0
    while True:
        block = os.read(fd, min(4096, maximum + 1 - size))
        if not block:
            return b"".join(pieces)
        pieces.append(block)
        size += len(block)
        if size > maximum:
            raise ResourceUnavailable("COUNTER_OVERSIZE")


class MemorySource:
    """Pinned, read-only membership and visible ancestor counters.

    This object has no thresholds, sampler, signal or launch capability. The
    caller must separately qualify its workload budget and operation controller.
    """

    def __init__(self, mount: Path, member: tuple[str, ...]):
        self._fds: list[int] = []
        self._nodes: list[tuple[int, int, int]] = []
        self._identities: dict[int, tuple[int, int]] = {}
        self._pid = os.getpid()
        try:
            if sys.platform != "linux":
                raise ResourceUnavailable("UNSUPPORTED_PLATFORM")
            if not mount.is_absolute() or any(
                part in ("", ".", "..") or "/" in part for part in member
            ):
                raise ResourceUnavailable("SOURCE_PATH")
            if ".." in mount.parts:
                raise ResourceUnavailable("SOURCE_PATH")
            # Mountinfo describes a kernel filesystem; its root is not a path
            # to normalize against /proc/self/cgroup's namespace-relative view.
            mounts = [
                line.split()
                for line in Path("/proc/self/mountinfo").read_text().splitlines()
                if " - cgroup2 " in line
            ]
            matches = [row for row in mounts if row[4] == str(mount)]
            if len(matches) != 1:
                raise ResourceUnavailable("CGROUP2_MOUNT")
            parent = self._open(Path("/"), directory=True)
            for part in mount.parts[1:]:
                parent = self._open(part, directory=True, parent=parent)
            major, minor = map(int, matches[0][2].split(":"))
            device = os.fstat(parent).st_dev
            if (os.major(device), os.minor(device)) != (major, minor):
                raise ResourceUnavailable("MOUNT_DEVICE")
            self._append_node(parent)
            for part in member:
                parent = self._open(part, directory=True, parent=parent)
                if os.fstat(parent).st_dev != device:
                    raise ResourceUnavailable("ANCESTOR_DEVICE")
                self._append_node(parent)
            self._members = self._open("cgroup.procs", parent=parent)
            self.read()
        except BaseException:
            self.close()
            raise

    def _open(self, path, *, directory: bool = False, parent=None) -> int:
        flags = os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK
        if directory:
            flags |= os.O_DIRECTORY
        fd = os.open(path, flags, dir_fd=parent)
        self._fds.append(fd)
        metadata = os.fstat(fd)
        if not directory and not stat.S_ISREG(metadata.st_mode):
            raise ResourceUnavailable("COUNTER_TYPE")
        self._identities[fd] = (metadata.st_dev, metadata.st_ino)
        return fd

    def _append_node(self, directory: int) -> None:
        self._nodes.append(
            (
                directory,
                self._open("memory.current", parent=directory),
                self._open("memory.max", parent=directory),
            )
        )

    def _membership(self) -> None:
        raw = _read(self._members)
        if raw and (not raw.endswith(b"\n") or any(
            not item.isdigit() or int(item) <= 0 for item in raw.splitlines()
        )):
            raise ResourceUnavailable("MEMBERSHIP_SCHEMA")
        if self._pid not in [int(item) for item in raw.splitlines()]:
            raise ResourceUnavailable("SELF_NOT_WITNESSED")

    def read(self) -> MemoryObservation:
        if not self._fds or os.getpid() != self._pid:
            raise ResourceUnavailable("SOURCE_LIFETIME")
        self._membership()
        constraints = []
        for directory, current_fd, limit_fd in self._nodes:
            metadata = os.fstat(directory)
            current = parse_counter(_read(current_fd))
            assert current is not None
            constraints.append(MemoryConstraint(
                metadata.st_dev, metadata.st_ino, current,
                parse_counter(_read(limit_fd), allow_max=True),
            ))
        self._membership()
        for fd, identity in self._identities.items():
            metadata = os.fstat(fd)
            if (metadata.st_dev, metadata.st_ino) != identity:
                raise ResourceUnavailable("SOURCE_IDENTITY")
        margins = [max(0, c.limit - c.current) for c in constraints if c.limit is not None]
        if not margins:
            raise ResourceUnavailable("NO_VISIBLE_FINITE_LIMIT")
        return MemoryObservation(self._pid, time.monotonic_ns(), tuple(constraints), min(margins))

    def close(self) -> None:
        while self._fds:
            os.close(self._fds.pop())

    def __enter__(self) -> MemorySource:
        return self

    def __exit__(self, *_args) -> None:
        self.close()
