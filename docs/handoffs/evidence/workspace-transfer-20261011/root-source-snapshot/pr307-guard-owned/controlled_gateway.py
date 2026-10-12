"""Local controlled acquisition only: never call the installed real gh binary."""
import ast
import hashlib
import json
import os
import stat
import subprocess
import sys
from pathlib import Path

owned = Path(__file__).resolve().parent
package = Path("/workspace/engineering/pr307/action_server")
destination = package / "src/actions/server/_oauth2_config.py"
before = destination.read_bytes() if destination.exists() else None
before_mode = stat.S_IMODE(destination.stat().st_mode) if destination.exists() else None
bin_dir = owned / "controlled-bin"
bin_dir.mkdir(exist_ok=True)
fake = bin_dir / "gh"
fake.write_text("#!" + sys.executable + "\n" + '''import json,os,sys
from pathlib import Path
root=Path(__file__).resolve().parents[1]
name=sys.argv[-1].rsplit("/",1)[-1]
assert sys.argv[1:4]==["api","-H","Accept: application/vnd.github.raw"]
assert sys.argv[-1].startswith("repos/Sema4AI/oauth-public-configs/contents/")
assert name in ("actions-oauth-config.yaml","oauth-config.yaml")
parent=Path("/proc")/str(os.getppid())
identity={"input":name,"helper_pid":os.getppid(),"helper_argv0":parent.joinpath("cmdline").read_bytes().split(b"\\0")[0].decode(),"helper_exe":os.readlink(parent/"exe")}
with (root/"gateway-children.jsonl").open("a") as stream: stream.write(json.dumps(identity)+"\\n")
if os.environ.get("CONTROLLED_OAUTH_SECOND_FAILURE")=="1" and name=="oauth-config.yaml":
 sys.stderr.write("private acquisition body must be withheld\\n");sys.exit(17)
sys.stdout.buffer.write(b"formatVersion: '1.0.0'\\noauth2Config:\\n  providers: {}\\n")
''')
fake.chmod(0o700)
env = os.environ.copy()
env.pop("GH_TOKEN", None)
env.pop("GITHUB_TOKEN", None)
env["PATH"] = str(bin_dir) + os.pathsep + env["PATH"]
env["VIRTUAL_ENV"] = str(owned / "foreign-outer-tool-environment")
command = [sys.executable, str(owned / "outer_invoke_no_yaml.py"), str(package)]
source_files = [package / "tasks.py", package / "scripts/build_oauth2_config.py"]
source_hashes = {str(p.relative_to(package.parent)): hashlib.sha256(p.read_bytes()).hexdigest() for p in source_files}
source_tuple = subprocess.check_output(["git", "log", "-1", "--format=%H %T %P"], cwd=package.parent, text=True).strip().split()
results = []
try:
    for case in ("valid_structural_pair", "second_acquisition_failure"):
        case_env = env.copy()
        if case == "second_acquisition_failure":
            case_env["CONTROLLED_OAUTH_SECOND_FAILURE"] = "1"
        previous = destination.read_bytes() if destination.exists() else None
        result = subprocess.run(command, env=case_env, capture_output=True, timeout=90)
        (owned / (case + ".stdout.log")).write_bytes(result.stdout)
        (owned / (case + ".stderr.log")).write_bytes(result.stderr)
        assert b"private acquisition body" not in result.stdout + result.stderr
        if case == "valid_structural_pair":
            assert result.returncode == 0, result.stderr.decode()
            contents = next(ast.literal_eval(n.value) for n in ast.parse(destination.read_bytes()).body if isinstance(n, ast.Assign))
            assert set(contents) == {"actions_config", "default_user_config"}
            assert all("providers: {}" in v for v in contents.values())
        else:
            assert result.returncode != 0
            assert b"(exit 17)" in result.stdout + result.stderr
            assert destination.read_bytes() == previous
        results.append({"case":case,"exit_code":result.returncode,"module_sha256":hashlib.sha256(destination.read_bytes()).hexdigest(),"private_cause_withheld":True})
    identities = [json.loads(line) for line in (owned / "gateway-children.jsonl").read_text().splitlines()]
    assert len(identities) == 4
    assert all(Path(i["helper_argv0"]).parent == package / ".venv/bin" for i in identities)
    preflight = subprocess.run(["poetry", "run", "python", "-c", "import yaml,sys,json;print(json.dumps({'python':sys.executable,'prefix':sys.prefix,'yaml':yaml.__version__,'yaml_origin':yaml.__file__}))"], cwd=package, env={k:v for k,v in env.items() if k not in ("VIRTUAL_ENV", "POETRY_ACTIVE", "CONDA_PREFIX", "CONDA_DEFAULT_ENV", "PYTHONHOME", "PYTHONPATH")}, check=True, capture_output=True, text=True, timeout=30)
    yaml_identity = json.loads(preflight.stdout)
    assert Path(yaml_identity["prefix"]) == package / ".venv"
    assert Path(yaml_identity["yaml_origin"]).is_relative_to(package / ".venv")
    (owned / "controlled-gateway-receipt.json").write_text(json.dumps({"source": {"head": source_tuple[0], "tree": source_tuple[1], "parents": source_tuple[2:], "guard_file_sha256": source_hashes},"outer_yaml_forbidden":True,"outer_interpreter":sys.executable,"actual_invoke_task":True,"actual_package_poetry_helper":True,"source_acquisition":"mock gh on owned PATH only; no network","structural_fixture_is_not_release_content":True,"command":command,"cases":results,"helper_processes":identities,"package_yaml":yaml_identity,"generated_module_restored_in_finally":True},indent=2)+"\n")
finally:
    if before is None:
        destination.unlink(missing_ok=True)
    else:
        destination.write_bytes(before)
        destination.chmod(before_mode)
    assert list(destination.parent.glob(".oauth2-config-*.tmp")) == []
    assert {str(p.relative_to(package.parent)): hashlib.sha256(p.read_bytes()).hexdigest() for p in source_files} == source_hashes
