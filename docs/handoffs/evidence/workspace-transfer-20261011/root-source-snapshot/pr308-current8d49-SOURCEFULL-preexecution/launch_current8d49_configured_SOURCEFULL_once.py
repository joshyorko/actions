import hashlib
import json
import os
import stat
import subprocess
import sys
import time
import traceback
from pathlib import Path

O = Path(__file__).resolve().parent
assert len(sys.argv) == 3
cfg_path = O / "frozen-current8d49-source-FULL-inputs.json"
cfg = json.loads(cfg_path.read_text())

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def check(row):
    path = Path(row["path"])
    assert path.is_file() and not path.is_symlink()
    assert path.stat().st_size == row["bytes"] and sha(path) == row["sha256"]
    assert oct(stat.S_IMODE(path.stat().st_mode)) == row["mode"]

assert cfg["execution_enablement"] == "ROOT_CURRENT_SOURCE_GATES_ADOPTED_ONCE"
assert cfg["phase"] == "FULL"
assert cfg["head"] == "8d49d0865ad5ad27b2d4e325ec135212080625e8"
assert cfg["tree"] == "a80600809d373038ca76e445ba0b7b79bb7eeaa6"
assert not sys.flags.optimize and not os.environ.get("PYTHONOPTIMIZE")
release_path = Path(sys.argv[1])
assert sha(release_path) == sys.argv[2]
release = json.loads(release_path.read_text())
assert release["status"] == "ROOT_RELEASE_ONE_SERIALIZED_CURRENT_8D49_SOURCE_FULL"
assert release["proposal_sha256"] == sha(O / "OWNERFINAL-current8d49-configured-SOURCEFULL-preexecution-proposal.json")
proposal = json.loads((O / "OWNERFINAL-current8d49-configured-SOURCEFULL-preexecution-proposal.json").read_text())
for row in proposal["frozen_input_bindings"]:
    check(row)
assert release["source"] == cfg["head"] and release["tree"] == cfg["tree"]
assert release["serialized_no_other_heavy_or_installer"] is True
assert release["current_storage_independent_GO"] is True
for key in ("current_source_independent_review", "current_full_preexecution_independent_review"):
    assert release[key] and release[key]["path"] != str(release_path)
    check(release[key])
assert release["current_source_independent_review"]["path"] != release["current_full_preexecution_independent_review"]["path"]
for row in cfg["implementation_bindings"] + cfg["prepared_environment_and_RCC_bindings"]:
    check(row)
assert Path(sys.prefix).resolve() == Path(cfg["cached_toolkit_prefix"]).resolve()
for key, value in cfg["expected_activation_exports"].items():
    assert os.environ.get(key) == value, key
assert len(cfg["expected_activation_exports"]) == 18
assert os.environ["PATH"].split(os.pathsep)[0] == "/workspace/actions-cloud/bin"
for key in cfg["forbidden_actual_operator_exports"]:
    assert key not in os.environ
assert "PYTEST_ADDOPTS" not in os.environ, "INHERITED_PYTEST_ADDOPTS_REJECTED"
assert os.statvfs("/workspace").f_bavail * os.statvfs("/workspace").f_frsize >= cfg["capacity_floor_bytes"]
assert os.statvfs("/tmp").f_bavail * os.statvfs("/tmp").f_frsize >= cfg["tmp_capacity_floor_bytes"]
parent = Path(cfg["pytest_owned_parent"])
assert parent.parent == Path("/tmp") and not parent.exists() and not parent.is_symlink()
os.umask(0o077)
parent.mkdir(mode=0o700)
os.environ["PYTEST_XDIST_AUTO_NUM_WORKERS"] = "2"
os.environ["PYTEST_ADDOPTS"] = cfg["pytest_addopts"]
assert not Path(cfg["pytest_basetemp"]).exists()
owned = Path(cfg["owned_evidence_root"])
assert not owned.exists() and not owned.is_symlink()
owned.mkdir(mode=0o700)
log = owned / "original-FULL-source.private.log"
guard = [sys.executable, str(O / "current8d49_readonly_FULL_source_and_storage_guard.py"), str(cfg_path)]
guard_tail = [str(release_path), sys.argv[2]]
records = []
primary = post = None
primary_error = post_error = None
started = False
begin = time.monotonic()
with log.open("xb") as stream:
    try:
        before = ["timeout", "--signal=TERM", "--kill-after=10s", "120s", *guard, "before", *guard_tail]
        cp = subprocess.run(before, cwd=cfg["source_root"], stdout=stream, stderr=subprocess.STDOUT)
        records.append({"stage": "before", "returncode": cp.returncode})
        if cp.returncode:
            raise RuntimeError("BEFORE_FAILED_PRIMARY_NOT_STARTED")
        started = True
        full = ["timeout", "--signal=TERM", "--kill-after=10s", "640s", "timeout", "--signal=TERM", "--kill-after=10s", "600s", sys.executable, str(O / "current8d49_configured_FULL_body.py")]
        cp = subprocess.run(full, cwd=cfg["source_root"], stdout=stream, stderr=subprocess.STDOUT)
        primary = cp.returncode
        records.append({"stage": "FULL", "argv": full, "returncode": primary})
    except BaseException as error:
        primary_error = type(error).__name__
        stream.write(traceback.format_exc().encode())
    finally:
        try:
            after = ["timeout", "--signal=TERM", "--kill-after=10s", "120s", *guard, "after", *guard_tail]
            cp = subprocess.run(after, cwd=cfg["source_root"], stdout=stream, stderr=subprocess.STDOUT)
            post = cp.returncode
            records.append({"stage": "after-always", "returncode": post})
        except BaseException as error:
            post_error = type(error).__name__
            stream.write(traceback.format_exc().encode())
status = "PASS" if started and primary == 0 and primary_error is None and post == 0 and post_error is None else "FAIL/HOLD"
terminal = {"source": cfg["head"], "tree": cfg["tree"], "phase": "FULL", "status": status, "primary_started": started, "primary": primary, "primary_error": primary_error, "post": post, "post_error": post_error, "records": records, "seconds": time.monotonic() - begin, "log": {"path": str(log), "sha256": sha(log), "bytes": log.stat().st_size}, "native": "NOT_RUN", "scratch": "PRESERVE_ALL_NO_CLEANUP", "attempt": "CONSUMED_NO_AUTOMATIC_RETRY"}
path = owned / "original-terminal.json"
path.write_text(json.dumps(terminal, indent=2) + "\n")
path.chmod(0o600)
print(json.dumps({"status": status, "path": str(path), "sha256": sha(path), "bytes": path.stat().st_size}))
raise SystemExit(0 if status == "PASS" else 10)
