"""Atomic no-replace rename, not source/root identity or permission admission."""

import ctypes
import errno
import os
import sys
from pathlib import Path


def rename_directory_no_replace(source: Path, destination: Path) -> None:
    """Publish a complete same-filesystem directory without replacing any entry.

    Unsupported libc/kernel/filesystem capabilities fail closed. There is no
    replacing-rename, copy, or early-visible final-directory fallback. Callers
    still own source validation, trusted-parent admission and identity pinning.
    """
    if sys.platform == "win32":
        # Python documents Windows rename as raising FileExistsError whenever
        # dst exists. CPython uses MoveFileExW without MOVEFILE_REPLACE_EXISTING.
        # https://docs.python.org/3/library/os.html#os.rename
        os.rename(source, destination)
        return

    if sys.platform == "linux":
        symbol, cwd_fd, exclusive = "renameat2", -100, 1  # RENAME_NOREPLACE
    elif sys.platform == "darwin":
        symbol, cwd_fd, exclusive = "renameatx_np", -2, 4  # RENAME_EXCL
    else:
        raise OSError(errno.ENOTSUP, "Atomic no-replace publication is unsupported")

    library = ctypes.CDLL(None, use_errno=True)
    rename = getattr(library, symbol, None)
    if rename is None:
        raise OSError(errno.ENOTSUP, "Atomic no-replace rename is unavailable")
    rename.argtypes = [
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_uint,
    ]
    rename.restype = ctypes.c_int
    if rename(cwd_fd, os.fsencode(source), cwd_fd, os.fsencode(destination), exclusive):
        error = ctypes.get_errno()
        raise OSError(error, "Atomic no-replace directory publication failed")
