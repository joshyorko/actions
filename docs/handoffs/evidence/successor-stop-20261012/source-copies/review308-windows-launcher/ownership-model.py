import ast, json, subprocess, sys, hashlib
from pathlib import Path
from types import SimpleNamespace
head = "d358f9c2b41b9575a286e6a98cacf7425d694ea6"
source = subprocess.check_output(["git", "-C", "/workspace/actions-pr308", "show", head + ":action_server/tests/action_server_tests/test_dakota_rcc_acceptance.py"])
tree = ast.parse(source)
helper = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_capture_provider_fixture_child")
regression = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "test_provider_startup_failure_uses_bounded_kill_fallback")
final = next(n.finalbody for n in regression.body if isinstance(n, ast.Try) and n.finalbody)
helper_code = compile(ast.fix_missing_locations(ast.Module(body=[helper], type_ignores=[])), head, "exec")
final_code = compile(ast.fix_missing_locations(ast.Module(body=final, type_ignores=[])), head, "exec")
previous = sys.modules.get("psutil")
controls = []
def check(name, ok):
    assert ok, name
    controls.append({"name": name, "pass": bool(ok)})
class Missing(Exception):
    pass
try:
    for poison in ("verified_false", "snapshot_false", "root_changed_after_snapshot", "root_error", "valid"):
        calls = []
        child = SimpleNamespace(pid=777, create_time=lambda:20.0)
        root = SimpleNamespace(pid=123, create_time=lambda:10.0, children=lambda recursive:[child])
        def lookup(pid):
            calls.append(pid)
            if poison == "root_error":
                raise PermissionError()
            if pid == 123:
                return SimpleNamespace(pid=123,create_time=lambda:99.0) if poison == "root_changed_after_snapshot" and calls.count(123)>1 else root
            return child
        sys.modules["psutil"] = SimpleNamespace(Process=lookup, NoSuchProcess=Missing)
        ns = {}
        exec(helper_code, ns)
        owner = SimpleNamespace(pid=123,create_time=10.0,process=SimpleNamespace(poll=lambda:None),capture_verified=poison!="verified_false",snapshot_complete=poison!="snapshot_false")
        try:
            result = ns["_capture_provider_fixture_child"](owner,777)
            accepted = True
        except (AssertionError,PermissionError):
            accepted = False
        check("capture_"+poison, accepted if poison == "valid" else not accepted)
        if poison in ("verified_false","snapshot_false"):
            check("capture_"+poison+"_no_process_lookup", not calls)
    for observation in ("same_birth", "reused", "missing", "unreadable"):
        events = []
        child = SimpleNamespace(pid=777,kill=lambda:events.append("descendant_kill"))
        def lookup(pid):
            assert pid == 777
            if observation == "missing":raise Missing()
            if observation == "unreadable":raise PermissionError()
            return SimpleNamespace(create_time=lambda:99.0 if observation == "reused" else 20.0)
        sys.modules["psutil"] = SimpleNamespace(Process=lookup,NoSuchProcess=Missing)
        process = SimpleNamespace(poll=lambda:None,kill=lambda:events.append("original_popen_kill"),wait=lambda timeout:events.append(("original_popen_wait",timeout)),stdout=SimpleNamespace(close=lambda:events.append("stdout_close")),stderr=SimpleNamespace(close=lambda:events.append("stderr_close")))
        ns = {"fixture_descendants":[(child,20.0)],"captured":[process]}
        try:
            exec(final_code, ns)
            raised = False
        except PermissionError:
            raised = True
        check("teardown_"+observation+"_descendant_authority", ("descendant_kill" in events) == (observation == "same_birth"))
        check("teardown_"+observation+"_original_popen_finally", events[-4:] == ["original_popen_kill",("original_popen_wait",2),"stdout_close","stderr_close"])
        if observation == "unreadable":check("teardown_unreadable_remains_failure",raised)
finally:
    if previous is None:sys.modules.pop("psutil",None)
    else:sys.modules["psutil"] = previous
result = {"head":head,"test_source_sha256":hashlib.sha256(source).hexdigest(),"scope":"AST of exact capture and finally, fake process facts/methods only; no signals/native/real child", "controls":controls,"passed":len(controls)}
Path(__file__).with_name("ownership-model.json").write_text(json.dumps(result,indent=2)+"\n")
print(json.dumps({"passed":len(controls)}))
