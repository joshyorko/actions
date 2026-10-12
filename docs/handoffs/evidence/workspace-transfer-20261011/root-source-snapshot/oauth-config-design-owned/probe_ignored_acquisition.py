"""Read-only source diagnosis: mock gh; write only disposable external roots."""
import ast
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch

source = Path(__file__).with_name("pr307-tasks.py").read_bytes()
function = next(n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef) and n.name == "build_oauth2_config")
function.decorator_list = []
function.args.args[0].annotation = None
code = compile(ast.Module(body=[function], type_ignores=[]), "immutable-pr307-tasks.py", "exec")
results = []
for label, returncode, output in (
    ("nonzero_empty_stdout", 17, b""),
    ("nonzero_api_error_stdout", 1, b'{"message":"Not Found","documentation_url":"https://docs.github.com/rest","status":"404"}'),
):
    with tempfile.TemporaryDirectory(prefix="oauth-acq-probe-") as temporary:
        root = Path(temporary)
        dest = root / "src/actions/server/_oauth2_config.py"
        dest.parent.mkdir(parents=True)
        namespace = {"CURDIR": root}
        exec(code, namespace)
        with patch("subprocess.run", return_value=subprocess.CompletedProcess(["gh", "api"], returncode, stdout=output)) as call:
            namespace["build_oauth2_config"](None)
        tree = ast.parse(dest.read_bytes())
        contents = next(ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign))
        results.append({"case":label,"mocked_exit":returncode,"gh_call_count":call.call_count,"generated_despite_failure":True,"value_lengths":{k:len(v) for k,v in contents.items()},"module_sha256":hashlib.sha256(dest.read_bytes()).hexdigest()})
Path(__file__).with_name("ignored-acquisition-probe.json").write_text(json.dumps({"source_sha256":hashlib.sha256(source).hexdigest(),"cases":results,"no_network_or_repository_writes":True},indent=2)+"\n")
print(json.dumps(results,indent=2))
