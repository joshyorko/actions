"""Private cache-plan boundary. No product imports or native execution.

The source fixture admits/mounts only the same-version pkgs alias. This module
creates its root-owned marker; it never aliases a runtime/provider/Holotree.
"""
import hashlib
import json
import os
import stat
from pathlib import Path

from runner_contracts_v3 import need, parse_json_object


ENV_KEY = "ACTIONS_RUNTIME_RCC_TEST_PACKAGE_CACHE_CONFIG"
ROOTS = {
    "control3": "/dev/shm/actions-rcc-compatibility-actual-control3-20261011-owned-pkgs-3",
    "released5": "/dev/shm/actions-rcc-compatibility-actual-released5-20261011-owned-pkgs-1",
    "candidate7276": "/dev/shm/actions-rcc-compatibility-actual-candidate7276-20261011-owned-pkgs-1",
}


def encoded(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def cache_plan(config, label, source, tree, binaries):
    need(label in binaries, "CACHE_APPROVED_LABEL")
    need(config["source"] == source and config["tree"] == tree, "CACHE_SOURCE_TUPLE")
    binary = config["binary"]
    path, digest, selector, version = binaries[label]
    need(binary == {"path": path, "sha256": digest, "selector": selector, "version": version},
         "CACHE_APPROVED_BINARY")
    root = Path(config["owned_root"])
    need(root.is_absolute() and root.parent == Path("/dev/shm")
         and root.name.startswith("actions-rcc-compatibility-actual-" + label + "-")
         and ".." not in root.parts, "CACHE_PER_VERSION_ONCE_ROOT")
    need(str(root) == ROOTS[label], "CACHE_DISTINCT_FROZEN_ONCE_ROOT")
    marker = {"schema": 1, "runtime_source_sha": source, "runtime_source_tree": tree,
              "label": label, "binary_sha256": digest, "state_root": str(root),
              "package_cache_root": str(root / "actions-home" / "pkgs")}
    raw = encoded(marker)
    child_config = dict(marker, state_marker_sha256=sha(raw))
    expected = {"schema": 1, "marker": marker, "marker_sha256": sha(raw),
                "marker_path": str(root / "rcc-package-cache-owner.json"),
                "child_config": child_config, "environment_key": ENV_KEY,
                "cold_publication_then_warm_staged_pkgs_only": True}
    actual = config.get("owned_package_cache")
    # Exact JSON bytes distinguish 1/bool/float aliases and reject unknown keys.
    need(type(actual) is dict and encoded(actual) == encoded(expected), "CACHE_EXACT_PLAN")
    return expected


def bound_json(row):
    need(type(row) is dict and set(row) == {"path", "sha256", "bytes", "mode"},
         "CACHE_REVIEW_BINDING_SHAPE")
    path = Path(row["path"])
    meta = path.lstat()
    need(stat.S_ISREG(meta.st_mode) and not path.is_symlink(), "CACHE_REVIEW_REGULAR_FILE")
    raw = path.read_bytes()
    need(type(row["bytes"]) is int and len(raw) == row["bytes"] and sha(raw) == row["sha256"]
         and stat.S_IMODE(meta.st_mode) == int(str(row["mode"]), 8), "CACHE_REVIEW_HASH_MODE")
    return parse_json_object(raw)


def require_cache_release(config, release, config_sha, label, source, tree, binaries):
    plan = cache_plan(config, label, source, tree, binaries)
    need(type(release) is dict and "cache_plan_sha256" in release
         and "cache_configuration_independent" in release, "CACHE_ROOT_ADOPTION_REQUIRED")
    need(release["cache_plan_sha256"] == sha(encoded(plan)), "CACHE_ROOT_PLAN_HASH")
    review = bound_json(release["cache_configuration_independent"])
    required = {"schema": 1, "status": "INDEPENDENT_CURRENT_CACHE_CONFIG_GO",
                "source": source, "tree": tree, "label": label,
                "config_sha256": config_sha, "cache_plan_sha256": sha(encoded(plan))}
    need(all(key in review and encoded(review[key]) == encoded(value)
             for key, value in required.items()), "CACHE_INDEPENDENT_CURRENT_CONFIG_REQUIRED")
    # Keep original v6 release equality/admission, extended only by these fields.
    return {key: value for key, value in release.items()
            if key not in {"cache_plan_sha256", "cache_configuration_independent"}}


def _owned_directory(path):
    meta = path.lstat()
    need(stat.S_ISDIR(meta.st_mode) and not path.is_symlink()
         and path.resolve(strict=True) == path
         and stat.S_IMODE(meta.st_mode) == 0o700 and meta.st_uid == os.getuid(),
         "CACHE_OWNED_DIRECTORY")


def _owned_rcc_home(path):
    """Only the native-managed home may use0750, with current UID and GID."""
    meta = path.lstat()
    need(stat.S_ISDIR(meta.st_mode) and not path.is_symlink()
         and path.resolve(strict=True) == path
         and stat.S_IMODE(meta.st_mode) in (0o700, 0o750)
         and meta.st_uid == os.getuid() and meta.st_gid == os.getgid(),
         "CACHE_NATIVE_HOME_MODE_OWNER_GROUP")


def create_cache_marker(config, label, source, tree, binaries):
    plan = cache_plan(config, label, source, tree, binaries)
    root = Path(config["owned_root"])
    _owned_directory(root)
    _owned_rcc_home(root / "actions-home")
    cache = Path(plan["marker"]["package_cache_root"])
    need(not cache.exists() and not cache.is_symlink(), "CACHE_COLD_ROOT_MUST_BE_ABSENT")
    # Exclusivity retains unexpected existing/partial state instead of replacing.
    fd = os.open(plan["marker_path"], os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(encoded(plan["marker"]))
    cache.mkdir(mode=0o700)
    validate_created_cache(config, label, source, tree, binaries)
    need(not any(cache.iterdir()), "CACHE_INITIAL_EMPTY")
    return encoded(plan["child_config"]).decode().rstrip("\n")


def validate_created_cache(config, label, source, tree, binaries):
    plan = cache_plan(config, label, source, tree, binaries)
    root = Path(config["owned_root"])
    _owned_directory(root)
    _owned_rcc_home(root / "actions-home")
    _owned_directory(Path(plan["marker"]["package_cache_root"]))
    path = Path(plan["marker_path"])
    meta = path.lstat()
    need(stat.S_ISREG(meta.st_mode) and not path.is_symlink()
         and stat.S_IMODE(meta.st_mode) == 0o600 and meta.st_uid == os.getuid()
         and path.read_bytes() == encoded(plan["marker"]), "CACHE_MARKER_CHANGED")
