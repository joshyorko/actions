"""Explicit local trust-carrier profiles for the RCC Runtime adapter."""

from __future__ import annotations

import hashlib
import json
import os
import stat
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

TRUST_PROFILE_ENV = "ACTIONS_RUNTIME_RCC_TRUST_PROFILE"
TRUST_CARRIER_ENV = "ACTIONS_RUNTIME_RCC_TRUST_CARRIER"
TRUST_ROOT_ENV = "ACTIONS_RUNTIME_RCC_TRUST_ROOT"
PROVIDER_COUPLED_PROFILE = "provider-coupled-v1"
LOCAL_DETACHED_PROFILE = "local-detached-v1"


@dataclass(frozen=True)
class RccTrustProfile:
    """Trust selection that is separate from Environment Artifact content."""

    profile_id: str
    carrier_kind: str | None
    carrier_reference: str | None
    profile_digest: str

    def __post_init__(self) -> None:
        if self.profile_id == PROVIDER_COUPLED_PROFILE:
            if self.carrier_kind is not None or self.carrier_reference is not None:
                raise ValueError("provider-coupled profile cannot name a trust carrier")
        elif self.profile_id == LOCAL_DETACHED_PROFILE:
            if self.carrier_kind != "filesystem" or not self.carrier_reference:
                raise ValueError("local-detached profile requires a filesystem carrier")
        else:
            raise ValueError("unsupported RCC trust profile")
        if self.profile_digest != _profile_digest(
            self.profile_id, self.carrier_kind, self.carrier_reference
        ):
            raise ValueError("RCC trust profile digest mismatch")

    @property
    def is_local_detached(self) -> bool:
        return self.profile_id == LOCAL_DETACHED_PROFILE

    def rcc_arguments(self) -> list[str]:
        if not self.is_local_detached:
            return []
        if not self.carrier_reference:
            raise ValueError("local-detached trust carrier is unavailable")
        return [
            "--trust-carrier",
            self.carrier_reference,
            "--trust-carrier-type",
            "filesystem",
        ]


def _profile_digest(
    profile_id: str, carrier_kind: str | None, carrier_reference: str | None
) -> str:
    contract = (
        "rcc-runtime/v2" if profile_id == LOCAL_DETACHED_PROFILE else "rcc-runtime/v1"
    )
    payload = {
        "contract_version": contract,
        "profile_id": profile_id,
        "carrier_kind": carrier_kind,
        "carrier_reference": carrier_reference,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def provider_coupled_profile() -> RccTrustProfile:
    return RccTrustProfile(
        profile_id=PROVIDER_COUPLED_PROFILE,
        carrier_kind=None,
        carrier_reference=None,
        profile_digest=_profile_digest(PROVIDER_COUPLED_PROFILE, None, None),
    )


def profile_from_fields(
    profile_id: str,
    carrier_kind: str | None,
    carrier_reference: str | None,
    profile_digest: str,
) -> RccTrustProfile:
    """Recreate descriptor profile data without granting filesystem authority."""
    if profile_id not in {PROVIDER_COUPLED_PROFILE, LOCAL_DETACHED_PROFILE}:
        raise ValueError("unsupported RCC trust profile")
    if profile_id == PROVIDER_COUPLED_PROFILE:
        if carrier_kind is not None or carrier_reference is not None:
            raise ValueError("provider-coupled profile cannot name a trust carrier")
    elif carrier_kind != "filesystem" or not carrier_reference:
        raise ValueError("local-detached profile requires a filesystem carrier")
    expected = _profile_digest(profile_id, carrier_kind, carrier_reference)
    if profile_digest != expected:
        raise ValueError("RCC trust profile digest mismatch")
    return RccTrustProfile(profile_id, carrier_kind, carrier_reference, expected)


def _absolute_path(raw: str, name: str) -> Path:
    if not raw or "\x00" in raw:
        raise ValueError(f"{name} must be an absolute canonical path")
    path = Path(raw)
    if not path.is_absolute() or ".." in raw.split(os.sep) or str(path) != raw:
        raise ValueError(f"{name} must be an absolute canonical path")
    return path


def _require_posix_directory_support() -> None:
    if (
        os.name != "posix"
        or not hasattr(os, "geteuid")
        or not hasattr(os, "O_NOFOLLOW")
        or not hasattr(os, "O_DIRECTORY")
        or not hasattr(os, "O_CLOEXEC")
        or os.open not in os.supports_dir_fd
        or os.mkdir not in os.supports_dir_fd
    ):
        raise ValueError(
            "local-detached profile is unsupported: this platform cannot verify "
            "directory ownership and no-follow paths"
        )


def _open_root(path: Path) -> int:
    _require_posix_directory_support()
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    descriptor: int | None = os.open(path.anchor, flags)
    try:
        for component in path.parts[1:]:
            assert descriptor is not None
            child = os.open(component, flags, dir_fd=descriptor)
            metadata = os.fstat(child)
            mode = stat.S_IMODE(metadata.st_mode)
            if not stat.S_ISDIR(metadata.st_mode):
                os.close(child)
                raise ValueError("trust root path contains a non-directory")
            if mode & 0o022 and not (metadata.st_uid == 0 and mode & stat.S_ISVTX):
                os.close(child)
                raise ValueError(
                    "trust root path traverses a shared-writable directory"
                )
            os.close(descriptor)
            descriptor = child
        assert descriptor is not None
        root_metadata = os.fstat(descriptor)
        root_mode = stat.S_IMODE(root_metadata.st_mode)
        if root_metadata.st_uid != os.geteuid() or root_mode & 0o077:
            raise ValueError(
                "trust root must be owned and private for the current user"
            )
        if root_mode & 0o700 != 0o700:
            raise ValueError("trust root must be readable, writable, and searchable")
        result = descriptor
        descriptor = None
        return result
    except OSError as exc:
        raise ValueError(
            "trust root must exist with no symlink path components"
        ) from exc
    except BaseException:
        raise
    finally:
        if descriptor is not None:
            os.close(descriptor)


def _ensure_carrier(root: Path, carrier: Path, *, create: bool) -> str:
    try:
        relative = carrier.relative_to(root)
    except ValueError as exc:
        raise ValueError(
            "trust carrier must be contained by the allowed trust root"
        ) from exc
    if not relative.parts or relative == Path("."):
        raise ValueError(
            "trust carrier must be a private directory below the trust root"
        )

    root_fd = _open_root(root)
    descriptor = root_fd
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    try:
        for component in relative.parts:
            try:
                child = os.open(component, flags, dir_fd=descriptor)
            except FileNotFoundError:
                if not create:
                    raise ValueError("configured trust carrier directory is missing")
                os.mkdir(component, 0o700, dir_fd=descriptor)
                child = os.open(component, flags, dir_fd=descriptor)
            metadata = os.fstat(child)
            mode = stat.S_IMODE(metadata.st_mode)
            if not stat.S_ISDIR(metadata.st_mode):
                os.close(child)
                raise ValueError("trust carrier path contains a non-directory")
            if metadata.st_uid != os.geteuid() or mode & 0o077:
                os.close(child)
                raise ValueError("trust carrier directories must be owned and private")
            if mode & 0o700 != 0o700:
                os.close(child)
                raise ValueError(
                    "trust carrier directory must be readable, writable, and searchable"
                )
            if descriptor != root_fd:
                os.close(descriptor)
            descriptor = child
        return str(carrier)
    except OSError as exc:
        raise ValueError("trust carrier must have no symlink path components") from exc
    finally:
        if descriptor != root_fd:
            os.close(descriptor)
        os.close(root_fd)


def _overlaps_package(carrier: Path, package_roots: Sequence[Path]) -> bool:
    for package_root in package_roots:
        try:
            package = package_root.resolve(strict=True)
        except OSError as exc:
            raise ValueError(
                "package source root must exist to validate trust carrier"
            ) from exc
        if (
            carrier == package
            or carrier in package.parents
            or package in carrier.parents
        ):
            return True
    return False


def resolve_trust_profile(
    environment: Mapping[str, str],
    *,
    package_roots: Sequence[Path] = (),
    create_carrier: bool = True,
) -> RccTrustProfile:
    """Resolve trusted operator configuration and validate local carrier paths."""
    profile_value = environment.get(TRUST_PROFILE_ENV)
    root_value = environment.get(TRUST_ROOT_ENV)
    carrier_value = environment.get(TRUST_CARRIER_ENV)
    if profile_value is None:
        if root_value is not None or carrier_value is not None:
            raise ValueError("trust root/carrier requires an explicit trust profile")
        return provider_coupled_profile()
    if profile_value == PROVIDER_COUPLED_PROFILE:
        if root_value is not None or carrier_value is not None:
            raise ValueError(
                "provider-coupled profile does not accept a trust root/carrier"
            )
        return provider_coupled_profile()
    if profile_value != LOCAL_DETACHED_PROFILE:
        raise ValueError("unsupported RCC trust profile")
    if not root_value or not carrier_value:
        raise ValueError(
            "local-detached profile requires explicit trust root and carrier"
        )

    root = _absolute_path(root_value, "trust root")
    carrier = _absolute_path(carrier_value, "trust carrier")
    try:
        relative = carrier.relative_to(root)
    except ValueError as exc:
        raise ValueError(
            "trust carrier must be contained by the allowed trust root"
        ) from exc
    if not relative.parts:
        raise ValueError("trust carrier must be below the allowed trust root")
    if _overlaps_package(carrier, package_roots):
        raise ValueError("trust carrier must be outside selected package source")

    carrier_reference = _ensure_carrier(root, carrier, create=create_carrier)
    profile_digest = _profile_digest(
        LOCAL_DETACHED_PROFILE, "filesystem", carrier_reference
    )
    return RccTrustProfile(
        profile_id=LOCAL_DETACHED_PROFILE,
        carrier_kind="filesystem",
        carrier_reference=carrier_reference,
        profile_digest=profile_digest,
    )
