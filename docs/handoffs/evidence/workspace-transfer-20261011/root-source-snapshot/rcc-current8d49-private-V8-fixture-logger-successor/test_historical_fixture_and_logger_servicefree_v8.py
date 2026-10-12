import ast
import hashlib
import importlib
import importlib.util
import json
import os
import sys
from pathlib import Path

import pytest

OWN = Path(__file__).resolve().parent
sys.path.insert(0, str(OWN))
sys.path.insert(1, "/workspace/engineering/rcc-compatibility-owned-cache-runner-successor-preparation")
alias = importlib.import_module("historical_binding_current8d49_v8")
contracts = importlib.import_module("runner_contracts_v3")


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def bind(path):
    return dict(path=str(path), bytes=path.stat().st_size, sha256=digest(path.read_bytes()),
                mode=oct(path.stat().st_mode & 0o777))


def transport_path():
    if os.environ.get("PRIVATE_V8_FIXTURE_BASELINE") == "ORIGINAL":
        return Path("/workspace/engineering/rcc-current8d49-private-V8-content-preparation/actual_transport_v8.py")
    return OWN / "actual_transport_v8.py"


def load_transport():
    spec = importlib.util.spec_from_file_location("controlled_fixture_transport", transport_path())
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fixture_case(tmp_path, monkeypatch):
    live = tmp_path / "repository/action_server/tests/action_server_tests/fixture.py"
    live.parent.mkdir(parents=True)
    live.write_bytes(b"current live bytes distinct")
    live.chmod(0o600)
    snapshot = tmp_path / "old-snapshot.py"
    snapshot.write_bytes(b"historical exact Git body")
    snapshot.chmod(0o400)
    row = dict(path=str(live), bytes=snapshot.stat().st_size, sha256=digest(snapshot.read_bytes()), mode="0o600")
    old = dict(source=alias.HISTORICAL_FIXTURE_SOURCE, tree=alias.HISTORICAL_FIXTURE_TREE, bindings=[row.copy()])
    config = tmp_path / "old-qualified.json"
    state = dict(tree=alias.HISTORICAL_FIXTURE_TREE, mode="100644", body=snapshot.read_bytes())

    def config_binding():
        config.write_text(json.dumps(old))
        config.chmod(0o600)
        monkeypatch.setattr(alias, "HISTORICAL_FIXTURE_CONFIG", bind(config))

    def git(argv, **kwargs):
        command = argv[3:]
        if command[0] == "rev-parse":
            return state["tree"] + "\n"
        if command[0] == "ls-tree":
            return state["mode"] + " blob " + "1" * 40 + "\t" + alias.HISTORICAL_FIXTURE_GIT_PATH + "\n"
        if command[0] == "show":
            return state["body"]
        raise AssertionError("UNEXPECTED_READONLY_GIT_COMMAND")

    monkeypatch.setattr(alias, "HISTORICAL_FIXTURE", row.copy())
    monkeypatch.setattr(alias, "HISTORICAL_FIXTURE_SNAPSHOT", bind(snapshot))
    monkeypatch.setattr(alias.subprocess, "check_output", git)
    config_binding()
    before = live.read_bytes()
    assert alias.verify_historical_fixture(row)["raw_body_returned"] is False
    assert live.read_bytes() == before
    transport = load_transport()
    assert transport.read_bound(row) is None
    current = bind(live)
    assert current["path"] == row["path"] and current["sha256"] != row["sha256"]
    assert transport.read_bound(current) == before
    return row, old, config_binding, state, snapshot, live


def test_historical_transport_baseline_separates_exact_old_row_from_current_live(tmp_path, monkeypatch):
    fixture_case(tmp_path, monkeypatch)


@pytest.mark.parametrize("poison,category", [
    ("extra_original_key", "UNAPPROVED_HISTORICAL_FIXTURE"),
    ("wrong_old_source", "HISTORICAL_FIXTURE_SOURCE"),
    ("old_row_omitted", "HISTORICAL_FIXTURE_ORIGINAL_ROW"),
    ("old_row_duplicate", "HISTORICAL_FIXTURE_ORIGINAL_ROW"),
    ("changed_snapshot", "HISTORICAL_ALIAS_BODY"),
    ("wrong_snapshot_mode", "HISTORICAL_ALIAS_MODE"),
    ("wrong_git_tree", "HISTORICAL_FIXTURE_GIT_TREE"),
    ("wrong_git_mode", "HISTORICAL_FIXTURE_GIT_MODE_PATH"),
    ("wrong_git_body", "HISTORICAL_FIXTURE_GIT_BODY"),
])
def test_baseline_first_historical_fixture_poison_rejected(tmp_path, monkeypatch, poison, category):
    row, old, rebind_config, state, snapshot, live = fixture_case(tmp_path, monkeypatch)
    live_before = live.read_bytes()
    if poison == "extra_original_key":
        row["unknown"] = True
    elif poison == "wrong_old_source":
        old["source"] = "0" * 40
        rebind_config()
    elif poison == "old_row_omitted":
        old["bindings"] = []
        rebind_config()
    elif poison == "old_row_duplicate":
        old["bindings"].append(old["bindings"][0].copy())
        rebind_config()
    elif poison == "changed_snapshot":
        snapshot.chmod(0o600)
        snapshot.write_bytes(b"altered")
        snapshot.chmod(0o400)
    elif poison == "wrong_snapshot_mode":
        snapshot.chmod(0o600)
    elif poison == "wrong_git_tree":
        state["tree"] = "0" * 40
    elif poison == "wrong_git_mode":
        state["mode"] = "100755"
    else:
        state["body"] = b"wrong Git body"
    with pytest.raises(contracts.AdmissionFailure) as error:
        alias.verify_historical_fixture(row)
    assert error.value.code == category
    assert live.read_bytes() == live_before


def test_actual_logger_argv_uses_fresh_owned_root_and_all_retention(tmp_path):
    tree = ast.parse(transport_path().read_bytes())
    main = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "main")
    original = os.environ.get("PRIVATE_V8_FIXTURE_BASELINE") == "ORIGINAL"
    target = "command" if original else "logger"
    start = next(i for i, n in enumerate(main.body) if isinstance(n, ast.Assign)
                 and any(isinstance(t, ast.Name) and t.id == target for t in n.targets))
    statements = main.body[start:start + (2 if original else 4)]
    root = tmp_path / "fresh-once-owned-root"
    root.mkdir(mode=0o700)
    config = dict(python="/controlled/python", selectors=["exact-first", "exact-second"])
    expected = [config["python"], "-m", "pytest", "-n0", "-vv", "-rA", "-m",
                "integration_test and real_rcc", "--basetemp", str(root / "pytest"),
                "--robocorp-log-output", str(root / "pytest-logging"), "-o", "tmp_path_retention_policy=all",
                "--junitxml", str(root / "junit.xml"), *config["selectors"]]
    config["pytest_argv"] = ([config["python"], "-m", "pytest", "-n0", "-vv", "-rA", "-m",
                             "integration_test and real_rcc", "--basetemp", str(root / "pytest"),
                             "--junitxml", str(root / "junit.xml"), *config["selectors"]] if original else expected)
    ns = dict(root=root, config=config, need=contracts.need)
    exact = ast.Module(body=statements, type_ignores=[])
    exec(compile(exact, "actual-logger-exact-AST", "exec"), ns)
    assert ns["command"] == expected
    assert not (root / "pytest-logging").exists()
    (root / "pytest-logging").mkdir()
    with pytest.raises(contracts.AdmissionFailure) as error:
        exec(compile(exact, "actual-logger-exact-AST", "exec"), ns)
    assert error.value.code == "ACTUAL_LOGGER_MUST_BE_ABSENT"


@pytest.mark.parametrize("key,value,category", [
    ("path", "unapproved-missing-fixture.py", "UNAPPROVED_MISSING_BINDING"),
    ("sha256", "0" * 64, "INPUT_HASH_CHANGED"),
    ("mode", "0o400", "INPUT_HASH_CHANGED"),
])
def test_transport_wrong_historical_row_rejected_before_action(tmp_path, monkeypatch, key, value, category):
    row, *_ = fixture_case(tmp_path, monkeypatch)
    transport = load_transport()
    poisoned = dict(row, **{key: value})
    if key == "path":
        poisoned["path"] = str(tmp_path / value)
    action = []
    with pytest.raises(contracts.AdmissionFailure) as error:
        transport.read_bound(poisoned)
        action.append("UNREACHED_ACTION")
    assert error.value.code == category
    assert action == []


def test_actual_logger_symlink_rejected_before_command(tmp_path):
    tree = ast.parse((OWN / "actual_transport_v8.py").read_bytes())
    main = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "main")
    start = next(i for i, n in enumerate(main.body) if isinstance(n, ast.Assign)
                 and any(isinstance(t, ast.Name) and t.id == "logger" for t in n.targets))
    root = tmp_path / "own-root"
    root.mkdir(mode=0o700)
    (root / "pytest-logging").symlink_to(root / "absent")
    ns = dict(root=root, need=contracts.need)
    with pytest.raises(contracts.AdmissionFailure) as error:
        exec(compile(ast.Module(body=main.body[start:start+2], type_ignores=[]), "logger-symlink-AST", "exec"), ns)
    assert error.value.code == "ACTUAL_LOGGER_MUST_BE_ABSENT"
    assert "command" not in ns


@pytest.mark.parametrize("poison,category", [
    ("body", "TEMPORAL_SHARED_OUTPUT_BODY"),
    ("mtime", "TEMPORAL_SHARED_OUTPUT_METADATA"),
    ("inode", "TEMPORAL_SHARED_OUTPUT_METADATA"),
    ("boolean", "TEMPORAL_SHARED_OUTPUT_METADATA"),
    ("mode", "TEMPORAL_SHARED_OUTPUT_METADATA"),
    ("symlink", "TEMPORAL_SHARED_OUTPUT_FILE"),
    ("missing", "TEMPORAL_SHARED_OUTPUT_FILE"),
    ("duplicate", "TEMPORAL_SHARED_OUTPUT_PATH_SET"),
    ("unknown_key", "TEMPORAL_SHARED_OUTPUT_SCHEMA"),
])
def test_temporal_output_baseline_then_change_rejected(tmp_path, monkeypatch, poison, category):
    transport = load_transport()
    paths = [tmp_path / 'output.robolog', tmp_path / 'log.html']
    rows = []
    for path in paths:
        path.write_bytes(b'exact current body')
        path.chmod(0o600)
        st = path.stat()
        rows.append(dict(path=str(path), sha256=digest(path.read_bytes()), bytes=st.st_size,
                         mode=st.st_mode & 0o777, uid=st.st_uid, gid=st.st_gid, device=st.st_dev,
                         inode=st.st_ino, mtime_ns=st.st_mtime_ns))
    monkeypatch.setattr(transport, 'TEMPORAL_SHARED_OUTPUT_PATHS', tuple(map(str, paths)))
    transport.verify_temporal_shared_outputs(rows)
    if poison == 'body':
        saved=paths[0].stat();paths[0].write_bytes(b'wrong current body')
        os.utime(paths[0], ns=(saved.st_atime_ns, saved.st_mtime_ns))
    elif poison == 'mtime': rows[0]['mtime_ns'] += 1
    elif poison == 'inode': rows[0]['inode'] += 1
    elif poison == 'boolean': rows[0]['mode'] = True
    elif poison == 'mode': paths[0].chmod(0o400)
    elif poison == 'symlink': paths[0].unlink();paths[0].symlink_to(paths[1])
    elif poison == 'missing': paths[0].unlink()
    elif poison == 'duplicate': rows[1] = rows[0].copy()
    else: rows[0]['unknown'] = True
    action = []
    with pytest.raises(contracts.AdmissionFailure) as error:
        transport.verify_temporal_shared_outputs(rows)
        action.append('UNREACHED_ACTION')
    assert error.value.code == category
    assert action == []
