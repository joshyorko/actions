"""The provisional RCC Environment Artifact runtime boundary for spec-v2 Actions.

Only the digest in :class:`RccRuntimeDescriptor` is durable execution authority.
The RCC executable and receipt paths are local process evidence.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable, Sequence

RCC_VERSION = "v18.19.2"
RCC_CONTRACT_VERSION = "rcc-runtime/v1"
_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


class RccRuntimeError(RuntimeError):
    """A bounded failure at one RCC runtime preparation/execution phase."""

    def __init__(self, phase: str, message: str):
        self.phase = phase
        super().__init__(f"RCC {phase} failed: {message}")


@dataclass(frozen=True)
class RccRuntimeDescriptor:
    artifact_digest: str
    source_generation: str = "unknown"
    source_hash: str = "unknown"
    preparation_class: str = "local"
    rcc_version: str = RCC_VERSION
    runtime_kind: str = "rcc"
    contract_version: str = RCC_CONTRACT_VERSION

    def __post_init__(self) -> None:
        if not _DIGEST_RE.fullmatch(self.artifact_digest):
            raise RccRuntimeError("descriptor", "invalid sha256 artifact digest")
        if self.runtime_kind != "rcc":
            raise RccRuntimeError("descriptor", "unsupported runtime kind")
        if self.contract_version != RCC_CONTRACT_VERSION:
            raise RccRuntimeError("descriptor", "unsupported adapter contract")

    def to_dict(self) -> dict[str, object]:
        runtime = asdict(self)
        runtime["kind"] = runtime.pop("runtime_kind")
        return {"runtime": runtime}

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))

    @classmethod
    def from_dict(cls, value: object) -> "RccRuntimeDescriptor":
        if not isinstance(value, dict) or set(value) != {"runtime"}:
            raise RccRuntimeError("descriptor", "expected a versioned runtime descriptor")
        runtime = value["runtime"]
        if not isinstance(runtime, dict):
            raise RccRuntimeError("descriptor", "runtime namespace is not an object")
        allowed = {f.name for f in cls.__dataclass_fields__.values()} | {"kind"}
        if set(runtime) - allowed:
            raise RccRuntimeError("descriptor", "unknown runtime fields")
        runtime = dict(runtime)
        if "kind" in runtime:
            runtime["runtime_kind"] = runtime.pop("kind")
        try:
            return cls(**runtime)
        except TypeError as exc:
            raise RccRuntimeError("descriptor", "incomplete runtime descriptor") from exc

    @classmethod
    def from_json(cls, value: str) -> "RccRuntimeDescriptor":
        try:
            return cls.from_dict(json.loads(value))
        except RccRuntimeError:
            raise
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            raise RccRuntimeError("descriptor", "invalid descriptor JSON") from exc


def parse_artifact_digest(payload: object) -> str:
    """Extract exactly one canonical digest from an RCC JSON result."""

    candidates: list[object] = []
    if isinstance(payload, dict):
        for key in ("artifact", "artifact_digest", "artifactDigest", "digest"):
            if key in payload:
                candidates.append(payload[key])
        artifact = payload.get("artifact")
        if isinstance(artifact, dict) and "digest" in artifact:
            candidates.append(artifact["digest"])
        environment_artifact = payload.get("environment_artifact")
        if isinstance(environment_artifact, dict) and "digest" in environment_artifact:
            candidates.append(environment_artifact["digest"])
    values = []
    for candidate in candidates:
        if isinstance(candidate, str) and _DIGEST_RE.fullmatch(candidate):
            values.append(candidate)
        elif not isinstance(candidate, dict):
            raise RccRuntimeError("artifact", "missing or malformed artifact identity")
    values = list(dict.fromkeys(values))
    if len(values) != 1 or len(candidates) == 0:
        raise RccRuntimeError("artifact", "missing or malformed artifact identity")
    return values[0]


Runner = Callable[..., tuple[int, str, str]]


def _subprocess_runner(*args: str) -> tuple[int, str, str]:
    try:
        completed = subprocess.run(
            list(args),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=float(os.environ.get("ACTIONS_RUNTIME_RCC_TIMEOUT", "900")),
        )
    except subprocess.TimeoutExpired as exc:
        raise RccRuntimeError("rcc", "command timed out") from exc
    except OSError as exc:
        raise RccRuntimeError("rcc", str(exc)) from exc
    return completed.returncode, completed.stdout, completed.stderr


def _run_json(phase: str, args: Sequence[str], runner: Runner = _subprocess_runner) -> dict:
    code, stdout, stderr = runner(*args)
    if code:
        detail = (stderr or stdout).strip().splitlines()[-1:] or ["command failed"]
        raise RccRuntimeError(phase, detail[0][:400])
    try:
        loaded = json.loads(stdout)
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise RccRuntimeError(phase, "RCC did not return a JSON object") from exc
    if not isinstance(loaded, dict):
        raise RccRuntimeError(phase, "RCC returned a non-object JSON result")
    return loaded


def publish_artifact(environment: Path, rcc_location: Path, *, provider: str | None = None, runner: Runner = _subprocess_runner) -> str:
    args = [str(rcc_location), "env", "publish", "--environment", str(environment), "--json"]
    if provider:
        args.extend(["--provider", provider])
    return parse_artifact_digest(_run_json("publish", args, runner))


def acquire_artifact(artifact_digest: str, rcc_location: Path, *, provider: str | None = None, runner: Runner = _subprocess_runner) -> dict:
    if not _DIGEST_RE.fullmatch(artifact_digest):
        raise RccRuntimeError("acquire", "invalid artifact digest")
    args = [
        str(rcc_location), "env", "acquire", "--artifact", artifact_digest,
        "--json", "--permissive-local",
    ]
    if provider:
        args.extend(["--provider", provider])
    result = _run_json("acquire", args, runner)
    returned = parse_artifact_digest(result)
    if returned != artifact_digest:
        raise RccRuntimeError("acquire", "RCC returned a different artifact identity")
    return result


def prepare_runtime(
    environment: Path,
    rcc_location: Path,
    *,
    source_generation: str = "unknown",
    provider: str | None = None,
    runner: Runner = _subprocess_runner,
) -> RccRuntimeDescriptor:
    digest = publish_artifact(environment, rcc_location, provider=provider, runner=runner)
    acquire_artifact(digest, rcc_location, provider=provider, runner=runner)
    source_hash = hashlib.sha256(environment.read_bytes()).hexdigest()
    return RccRuntimeDescriptor(
        artifact_digest=digest, source_generation=source_generation, source_hash=source_hash
    )


def build_exec_command(
    rcc_location: Path,
    descriptor: RccRuntimeDescriptor,
    command: Sequence[str],
    *,
    receipt_file: Path | None,
    json_output: bool = True,
) -> list[str]:
    if receipt_file is None and command[:2] == ["python", "-c"]:
        pass
    args = [
        str(rcc_location), "env", "exec", "--artifact", descriptor.artifact_digest,
        "--permissive-local",
    ]
    if receipt_file is None and json_output:
        args.append("--json")
    elif receipt_file is not None:
        args.extend(["--inherit-streams", "--receipt-file", str(receipt_file)])
    args.extend(["--", *map(str, command)])
    return args


def load_descriptor(env_json: str) -> RccRuntimeDescriptor | None:
    try:
        value = json.loads(env_json)
    except (TypeError, ValueError, json.JSONDecodeError):
        return None
    if isinstance(value, dict) and "runtime" in value:
        return RccRuntimeDescriptor.from_dict({"runtime": value["runtime"]})
    return None


class RccProcessHandle:
    """Own and reap one RCC env-exec wrapper."""

    def __init__(self, process: subprocess.Popen, receipt_file: Path):
        self.process = process
        self.receipt_file = receipt_file

    @property
    def pid(self) -> int:
        return self.process.pid

    def kill(self) -> None:
        if self.process.poll() is None:
            from actions.server._common.process import kill_process_and_subprocesses

            kill_process_and_subprocesses(self.process.pid)
        self.process.wait()

    def wait(self, timeout: float | None = None) -> int:
        return self.process.wait(timeout=timeout)


def new_receipt_path(datadir: Path) -> Path:
    directory = datadir / "rcc-receipts"
    directory.mkdir(parents=True, exist_ok=True)
    return directory / f"{uuid.uuid4().hex}.json"


def get_rcc_location() -> Path:
    override = os.environ.get("ACTIONS_RUNTIME_RCC_BINARY")
    if override:
        path = Path(override)
        if not path.is_file() or not os.access(path, os.X_OK):
            raise RccRuntimeError("rcc", "ACTIONS_RUNTIME_RCC_BINARY is not executable")
        verify_rcc_version(path)
        return path
    from actions.server._download_rcc import get_default_rcc_location

    path = get_default_rcc_location()
    if not path.is_file() or not os.access(path, os.X_OK):
        raise RccRuntimeError("rcc", f"RCC executable unavailable for {RCC_VERSION}")
    verify_rcc_version(path)
    return path


def verify_rcc_version(rcc_location: Path, runner: Runner = _subprocess_runner) -> str:
    """Require the selected executable to be the released RCC contract."""

    code, stdout, stderr = runner(str(rcc_location), "--version")
    if code:
        raise RccRuntimeError("rcc", "unable to verify RCC version")
    version = stdout.strip()
    if version != RCC_VERSION:
        raise RccRuntimeError("rcc", f"unsupported RCC version {version!r}")
    return version


def read_receipt(receipt_file: Path, artifact_digest: str) -> dict:
    try:
        receipt = json.loads(receipt_file.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise RccRuntimeError("receipt", "missing or malformed RCC receipt") from exc
    if not isinstance(receipt, dict) or receipt.get("artifactDigest") != artifact_digest:
        raise RccRuntimeError("receipt", "receipt artifact identity mismatch")
    verification = receipt.get("verification")
    if not isinstance(verification, dict) or verification.get("valid") is not True:
        raise RccRuntimeError("receipt", "receipt verification is not valid")
    if not isinstance(receipt.get("leaseId"), str) or not receipt["leaseId"]:
        raise RccRuntimeError("receipt", "receipt lease identity is missing")
    return receipt
