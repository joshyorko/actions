"""Single owned TLS PostgreSQL fixture plus bounded installed Knowledge child."""
import argparse
import hashlib
import importlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import time
from uuid import uuid4

IMAGE = "postgres@sha256:f7d23353e1b15400d22ebe31189f4d314b87a4c129cc400c8c2d8d4ca127bf81"


def diagnostic(exc):
    frames = []
    tb = exc.__traceback__
    while tb is not None and len(frames) < 24:
        frames.append({"file": Path(tb.tb_frame.f_code.co_filename).name,
                       "function": tb.tb_frame.f_code.co_name,
                       "line": tb.tb_lineno})
        tb = tb.tb_next
    return {"type": type(exc).__module__ + "." + type(exc).__qualname__, "frames": frames}


class OwnedFixtureContainer:
    """Track exactly one pinned test fixture container and bound its cleanup."""
    def __init__(self, root, run):
        self.run_command = run
        self.cidfile = root / "owned-container.cid"
        self.name = "actions-knowledge-pg-" + uuid4().hex
        self.attempted = False
        self.uncertain = False
        self.container_id = None
        self.cleanup_steps = []

    def run(self, command, *args, **kwargs):
        kwargs.setdefault("timeout", 60)
        if list(command[:2]) != ["docker", "run"]:
            return self.run_command(command, *args, **kwargs)
        if (self.attempted or IMAGE not in command or "--cidfile" in command
                or "--name" in command):
            raise RuntimeError("Unexpected container launch")
        self.attempted = True
        scoped = [*command[:2], "--cidfile", str(self.cidfile), "--name", self.name,
                  *command[2:]]
        try:
            result = self.run_command(scoped, *args, **kwargs)
            self.capture_id()
            return result
        except BaseException as exc:
            self.uncertain = not isinstance(exc, subprocess.CalledProcessError)
            self.capture_id()
            raise

    def capture_id(self):
        if self.cidfile.exists():
            value = self.cidfile.read_text().strip()
            if not re.fullmatch(r"[0-9a-f]{64}", value):
                raise RuntimeError("Invalid owned container identity")
            self.container_id = value

    def inspect(self, target, timeout=10):
        deadline = time.monotonic() + timeout
        result = self.run_command(["docker", "inspect", "--type", "container", target],
                                  capture_output=True, text=True, timeout=timeout)
        if result.returncode:
            selector = "id=" + self.container_id if self.container_id else "name=^/" + self.name + "$"
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("Owned inspection deadline expired")
            listing = self.run_command(["docker", "container", "ls", "-a", "--no-trunc",
                                        "--filter", selector, "--format", "{{.ID}}"],
                                       capture_output=True, text=True, timeout=remaining)
            if listing.returncode == 0 and not listing.stdout.strip():
                return None
            raise RuntimeError("Owned container inspection failed")
        rows = json.loads(result.stdout)
        if len(rows) != 1 or rows[0]["Name"] != "/" + self.name:
            raise RuntimeError("Owned container name mismatch")
        value = rows[0]["Id"]
        if not re.fullmatch(r"[0-9a-f]{64}", value):
            raise RuntimeError("Invalid inspected container identity")
        if self.container_id is not None and value != self.container_id:
            raise RuntimeError("Owned container identity mismatch")
        self.container_id = value
        return value

    def cleanup(self):
        if not self.attempted:
            return {"status": "NOT_STARTED"}
        self.capture_id()
        target = self.container_id or self.name
        found = self.inspect(target)
        if found is None:
            if self.uncertain and self.container_id is None:
                raise RuntimeError("Container launch outcome remains uncertain")
            return {"status": "ALREADY_REMOVED", "container_id": self.container_id}
        errors, warnings = [], []
        for phase, command in (("stop", ["docker", "stop", "--time", "5", found]),
                               ("remove", ["docker", "rm", "-f", found])):
            step = {"phase": phase}
            self.cleanup_steps.append(step)
            try:
                result = self.run_command(command, capture_output=True, text=True, timeout=15)
                step["exit_code"] = result.returncode
                classification = "success"
                if result.returncode:
                    stderr = result.stderr.casefold()
                    if "no such container" in stderr or "no such object" in stderr:
                        classification = "already-absent"
                    elif "removal of container" in stderr and "is already in progress" in stderr:
                        classification = "removal-in-progress"
                    else:
                        classification = "unknown-command-error"
                        errors.append(classification)
                    if classification != "unknown-command-error":
                        warnings.append({"phase": phase, "classification": classification})
                step["classification"] = classification
            except BaseException as exc:
                step.update(classification="exception", exception=diagnostic(exc))
                errors.append("command-exception")
        final = {"phase": "final-exact-identity-inspection", "polls": 0}
        self.cleanup_steps.append(final)
        deadline = time.monotonic() + 15
        absent = False
        while time.monotonic() < deadline:
            final["polls"] += 1
            absent = self.inspect(found, timeout=min(3, deadline - time.monotonic())) is None
            if absent:
                break
            time.sleep(min(.25, max(0, deadline - time.monotonic())))
        final["classification"] = "confirmed-absent" if absent else "container-remains"
        if not absent:
            errors.append("container-remains")
        if errors:
            raise RuntimeError("Owned container cleanup did not finish cleanly")
        return {"status": "REMOVED", "container_id": found, "warnings": warnings}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--controller-root", type=Path, required=True)
    parser.add_argument("--supervisor", type=Path, required=True)
    parser.add_argument("--preflight-only", action="store_true")
    args = parser.parse_args()
    if sys.flags.optimize or sys.platform != "linux":
        raise RuntimeError("Linux checks required")
    config = json.loads(args.config.read_text())
    root = args.controller_root.absolute()
    # All source, artifact, install and compiler pins are checked before the
    # controller creates a root or starts the owned PostgreSQL container.
    if config.get("execution_authorized") is not True:
        raise RuntimeError("Candidate execution is not authorized")
    if (config.get("source_sha") != "88846b55e3b455eb44378bd5ba43bb146706661d"
            or config.get("source_tree_sha") != "a65449200ec36981b6ad4002147f19cf8da8a265"
            or config.get("runtime_version") != "1.1.0a56"
            or config.get("installed_base") != "/workspace/327-artifacts/a56"
            or config.get("core_version") != "1.1.0a8"
            or config.get("compiler_preparation_source_sha") != "aca51868d14e916c8034c69309e222100d5d50f3"
            or config.get("compiler_preparation_same_source") is not False):
        raise RuntimeError("Candidate identity differs from the admitted a56 source/profile")
    if config.get("fixture_root") != str(root / "fixture"):
        raise RuntimeError("Fresh fixture root must be the exact controller child")
    if config.get("postgres_image") != IMAGE:
        raise RuntimeError("Only the exact pinned PostgreSQL image is allowed")
    if config.get("tls_fixture_sha256") != "c588cca3478236276cc38a3ab965ba9100eb8271e591077f84b3d2907490b242":
        raise RuntimeError("TLS fixture source digest differs")
    if config.get("knowledge_postgres_contract_sha256") != "620bb8eee9199ff4af11446962452dd3ca322ebee0aef18711326e8044b44c4c":
        raise RuntimeError("Knowledge PostgreSQL contract source digest differs")
    if config.get("source_checkout") != "/workspace/actions":
        raise RuntimeError("Unexpected source checkout")
    expected_root = config.get("source_tree_sha")
    head = subprocess.run(["git", "-C", config["source_checkout"], "rev-parse", "HEAD"],
                          capture_output=True, text=True, timeout=10, check=True).stdout.strip()
    tree = subprocess.run(["git", "-C", config["source_checkout"], "rev-parse", "HEAD^{tree}"],
                          capture_output=True, text=True, timeout=10, check=True).stdout.strip()
    if head != config["source_sha"] or tree != expected_root:
        raise RuntimeError("Source checkout commit/tree differs")
    base = Path(config["installed_base"])
    for key, expected_status in (("artifact_receipt", "PASS_ARTIFACT_ONLY"),
                                 ("install_receipt", "PASS_CLEAN_INSTALL")):
        receipt_path = Path(config[key]).resolve(strict=True)
        if hashlib.sha256(receipt_path.read_bytes()).hexdigest() != config[key + "_sha256"]:
            raise RuntimeError(key + " digest differs")
        value = json.loads(receipt_path.read_text())
        if value.get("status") != expected_status:
            raise RuntimeError(key + " is not PASS")
    for key in ("build_supervisor_receipt", "install_supervisor_receipt"):
        receipt_path = Path(config[key]).resolve(strict=True)
        if hashlib.sha256(receipt_path.read_bytes()).hexdigest() != config[key + "_sha256"]:
            raise RuntimeError(key + " digest differs")
        value = json.loads(receipt_path.read_text())
        if value.get("status") != "PASS" or value.get("remaining_owned"):
            raise RuntimeError(key + " cleanup is not PASS")
    artifact = json.loads(Path(config["artifact_receipt"]).read_text())
    installed = json.loads(Path(config["install_receipt"]).read_text())
    if (artifact.get("source_commit") != config["source_sha"]
            or artifact.get("source_tree") != tree
            or artifact.get("wheel_sha256") != config["wheels"]["wheels/actions_runtime-1.1.0a56-cp312-cp312-linux_x86_64.whl"]
            or installed.get("runtime_version") != config["runtime_version"]
            or installed.get("runtime_wheel_sha256") != artifact.get("wheel_sha256")
            or installed.get("payload_member_count") != 339
            or installed.get("payload_verified_member_count") != 339
            or installed.get("metadata_identical") is not True
            or installed.get("pip_check") != "passed"):
        raise RuntimeError("a56 artifact/install qualification differs")
    if (base / "source-sha.txt").read_text().strip() != config["source_sha"]:
        raise RuntimeError("Installed candidate source marker differs")
    if not (base / "consumer/bin/python").is_file():
        raise RuntimeError("Installed candidate interpreter missing")
    for relative, digest in config["wheels"].items():
        if hashlib.sha256((base / relative).read_bytes()).hexdigest() != digest:
            raise RuntimeError("Installed wheel digest differs: " + relative)
    prepared = json.loads(Path(config["prepared_receipt"]).read_text())
    if (hashlib.sha256(Path(config["prepared_receipt"]).read_bytes()).hexdigest()
            != config["prepared_receipt_sha256"]
            or prepared.get("artifactDigest") != config["compiler_artifact_digest"]
            or prepared.get("packageYamlDigest") != "sha256:" + config["package_yaml_sha256"]):
        raise RuntimeError("Prepared compiler artifact/package binding differs")
    package_yaml = Path(config["package_yaml"]).read_bytes()
    if hashlib.sha256(package_yaml).hexdigest() != config["package_yaml_sha256"]:
        raise RuntimeError("Compiler package YAML digest differs")
    proof_path = Path(config["compiler_core_receipt"]).resolve(strict=True)
    if hashlib.sha256(proof_path.read_bytes()).hexdigest() != config["compiler_core_receipt_sha256"]:
        raise RuntimeError("Compiler Core proof digest differs")
    proof = json.loads(proof_path.read_text())
    if (proof.get("status") != "PASS" or proof.get("core_version") != "1.1.0a8"
            or proof.get("wheel_sha256") != config["compiler_core_wheel_sha256"]
            or config["compiler_core_wheel_sha256"] != config["wheels"]["wheels/actions_core-1.1.0a8-py3-none-any.whl"]):
        raise RuntimeError("Compiler Core proof differs from unchanged a8 pin")
    if root.exists() or root.is_symlink() or not root.parent.is_dir():
        raise RuntimeError("Fresh controller root and existing parent required")
    if shutil.disk_usage(root.parent).free < 10 * 1024**3:
        raise RuntimeError("Need at least 10 GiB free before starting fixture")
    inspected = subprocess.run(["docker", "image", "inspect", IMAGE, "--format", "{{.RepoDigests}} {{.Id}}"],
                               capture_output=True, text=True, timeout=10, check=True).stdout.strip()
    if IMAGE.removeprefix("docker.io/library/") not in inspected and IMAGE.split("@", 1)[1] not in inspected:
        raise RuntimeError("Pinned PostgreSQL image digest does not match local image")
    tests = Path(config["source_checkout"]).resolve() / "action_server/tests"
    tls_test = tests / "action_server_tests/test_sealed_postgres.py"
    knowledge_test = tests / "action_server_tests/test_knowledge_host_postgres.py"
    if hashlib.sha256(tls_test.read_bytes()).hexdigest() != config["tls_fixture_sha256"]:
        raise RuntimeError("TLS fixture source digest mismatch")
    if hashlib.sha256(knowledge_test.read_bytes()).hexdigest() != config["knowledge_postgres_contract_sha256"]:
        raise RuntimeError("Knowledge PostgreSQL contract source digest mismatch")
    if args.preflight_only:
        print(json.dumps({"status": "PASS_PREFLIGHT", "source": config["source_sha"],
                          "source_tree": tree, "runtime_version": config["runtime_version"],
                          "runtime_wheel_sha256": artifact["wheel_sha256"],
                          "compiler_artifact_digest": config["compiler_artifact_digest"],
                          "image": IMAGE, "image_inspect": inspected,
                          "services_started": False, "owned_root_created": False}))
        return 0
    root.mkdir(mode=0o700)
    candidate_site = Path(config["installed_base"]) / "consumer/lib/python3.12/site-packages"
    if not candidate_site.is_dir():
        raise RuntimeError("Installed candidate site-packages missing")
    sys.path.insert(0, str(candidate_site))
    for name in list(os.environ):
        if name.startswith("PG"):
            os.environ.pop(name)
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(tests))
    fixture_module = importlib.import_module("action_server_tests.test_sealed_postgres")
    if Path(fixture_module.__file__).resolve() != tls_test.resolve():
        raise RuntimeError("Imported TLS fixture is not candidate source")
    original_run = subprocess.run
    owner = OwnedFixtureContainer(root, original_run)

    class Factory:
        def mktemp(self, name):
            path = root / name
            path.mkdir(mode=0o700)
            return path

    fixture = None
    process = None
    def interrupt(signum, frame):
        raise KeyboardInterrupt()
    prior = {sig: signal.signal(sig, interrupt) for sig in (signal.SIGTERM, signal.SIGINT)}
    receipt = {"status": "RUNNING", "scope": "pinned owned TLS PostgreSQL fixture and installed public Knowledge acceptance",
               "source": config["source_sha"], "source_tree": config["source_tree_sha"],
               "runtime_version": config["runtime_version"],
               "artifact_receipt_sha256": config["artifact_receipt_sha256"],
               "install_receipt_sha256": config["install_receipt_sha256"],
               "compiler_preparation_source_sha": config["compiler_preparation_source_sha"],
               "compiler_preparation_same_source": config["compiler_preparation_same_source"],
               "compiler_artifact_digest": config["compiler_artifact_digest"],
               "image": IMAGE, "image_inspect": inspected, "cleanup_errors": []}
    bound_inputs = {
        "controller": Path(__file__).resolve(),
        "qualifier": Path(__file__).with_name("knowledge-qualify-a56-pg.py"),
        "ingest": Path(__file__).with_name("ingest.py"),
        "search": Path(__file__).with_name("search.py"),
        "child_supervisor": args.supervisor.resolve(),
        "candidate": args.config.resolve(),
        "tls_fixture_source": tests / "action_server_tests/test_sealed_postgres.py",
        "knowledge_postgres_source": tests / "action_server_tests/test_knowledge_host_postgres.py",
        "runtime_wheel": base / "wheels/actions_runtime-1.1.0a56-cp312-cp312-linux_x86_64.whl",
        "core_wheel": base / "wheels/actions_core-1.1.0a8-py3-none-any.whl",
        "work_items_wheel": base / "wheels/actions_work_items-0.5.0a2-py3-none-any.whl",
        "prepared_compiler_receipt": Path(config["prepared_receipt"]).resolve(),
        "compiler_package_yaml": Path(config["package_yaml"]).resolve(),
        "compiler_core_proof": Path(config["compiler_core_receipt"]).resolve(),
        "artifact_receipt": Path(config["artifact_receipt"]).resolve(),
        "install_receipt": Path(config["install_receipt"]).resolve(),
        "build_supervisor_receipt": Path(config["build_supervisor_receipt"]).resolve(),
        "install_supervisor_receipt": Path(config["install_supervisor_receipt"]).resolve(),
    }
    receipt["source_bound_inputs"] = {
        name: {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
        for name, path in bound_inputs.items()
    }
    try:
        subprocess.run = owner.run
        fixture = fixture_module.tls_postgres.__wrapped__(Factory())
        tls = next(fixture)
        from psycopg import sql
        writer_password = uuid4().hex
        with importlib.import_module("psycopg").connect(**tls.admin) as admin:
            admin.execute(sql.SQL("CREATE ROLE knowledge_writer LOGIN PASSWORD {} NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION").format(sql.Literal(writer_password)))
            admin.execute("GRANT CONNECT ON DATABASE postgres TO knowledge_writer")
            admin.execute("GRANT USAGE,CREATE ON SCHEMA public TO knowledge_writer")
            admin.execute("ALTER ROLE knowledge_writer SET temp_file_limit=0")
        password_path = root / "writer-password"
        password_path.write_text(writer_password)
        password_path.chmod(0o600)
        ca_path = root / "postgres-ca.pem"
        ca_path.write_bytes(tls.ca)
        ca_path.chmod(0o600)
        private = dict(config)
        private["postgres_fixture"] = {"host": "localhost", "port": tls.port,
                                       "database": "postgres", "username": "knowledge_writer",
                                       "writer_password_path": str(password_path),
                                       "ca_path": str(ca_path)}
        private_config = root / "candidate-private.json"
        private_config.write_text(json.dumps(private, indent=2) + "\n")
        private_config.chmod(0o600)
        child_env = dict(os.environ)
        for name in list(child_env):
            if name.startswith("PG"):
                child_env.pop(name)
        child_env["ACTIONS_KNOWLEDGE_CANDIDATE"] = str(private_config)
        supervisor_root = root / "supervisor"
        process = subprocess.Popen([str(Path(config["installed_base"]) / "consumer/bin/python"),
                                    "-I", str(args.supervisor.resolve()),
                                    "--candidate-python", str(Path(config["installed_base"]) / "consumer/bin/python"),
                                    "--script", str(Path(__file__).with_name("knowledge-qualify-a56-pg.py")),
                                    "--config", str(private_config),
                                    "--config-env", "ACTIONS_KNOWLEDGE_CANDIDATE",
                                    "--evidence-root", str(supervisor_root),
                                    "--budget-root", str(root)],
                                   env=child_env, stdin=subprocess.DEVNULL,
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                   start_new_session=True)
        process.wait(timeout=850)
        receipt["child_exit_code"] = process.returncode
        if process.returncode != 0:
            raise RuntimeError("Installed Knowledge supervisor failed")
        receipt["supervisor_receipt"] = json.loads((supervisor_root / "receipt.json").read_text())
        receipt["knowledge_receipt"] = json.loads((Path(config["fixture_root"]) / "evidence/receipt.json").read_text())
        receipt["status"] = "PASS"
    except BaseException as exc:
        receipt.update(status="FAILED", failure=diagnostic(exc))
    finally:
        for sig in prior:
            signal.signal(sig, signal.SIG_IGN)
        try:
            if process and process.poll() is None:
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=20)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait(timeout=5)
                    receipt["cleanup_errors"].append({"phase": "supervisor-stop", "type": "ForcedKill"})
        except BaseException as exc:
            receipt["cleanup_errors"].append({"phase": "supervisor-stop", "failure": diagnostic(exc)})
        try:
            if fixture is not None:
                fixture.close()
        except BaseException as exc:
            receipt["cleanup_errors"].append({"phase": "fixture-stop", "failure": diagnostic(exc)})
        try:
            receipt["owned_container_cleanup"] = owner.cleanup()
        except BaseException as exc:
            receipt["cleanup_errors"].append({"phase": "owned-container-cleanup", "failure": diagnostic(exc)})
        receipt["owned_container_identity"] = {"name": owner.name, "id": owner.container_id,
                                                "launch_attempted": owner.attempted,
                                                "launch_uncertain": owner.uncertain}
        receipt["owned_container_cleanup_steps"] = owner.cleanup_steps
        subprocess.run = original_run
        if receipt["cleanup_errors"]:
            receipt["status"] = "FAILED"
        receipt["fixture_bytes"] = sum(p.stat().st_size for p in root.rglob("*") if p.is_file())
        receipt["free_bytes"] = shutil.disk_usage(root).free
        if shutil.disk_usage(root).free < 10 * 1024**3:
            receipt["status"] = "FAILED"
            receipt["cleanup_errors"].append({"phase": "final-disk-floor", "type": "DiskFloor"})
        (root / "controller-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
        (root / "controller-receipt.json").chmod(0o600)
        for sig, handler in prior.items():
            signal.signal(sig, handler)
    return 0 if receipt["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
