import ast
import hashlib
import importlib
import json
import os
import stat
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

OWN = Path(__file__).resolve().parent
sys.path.insert(0, str(OWN))
sys.path.insert(1, "/workspace/engineering/rcc-compatibility-owned-cache-runner-successor-preparation")
alias = importlib.import_module("historical_binding_current8d49_v8")
contracts = importlib.import_module("runner_contracts_v3")
SOURCE = "8d49d0865ad5ad27b2d4e325ec135212080625e8"
TREE = "a80600809d373038ca76e445ba0b7b79bb7eeaa6"


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def source_guard_case():
    selected = os.environ.get("PRIVATE_V8_COUNT_ALIAS_BASELINE", "CURRENT")
    assert selected in ("CURRENT", "ORIGINAL")
    source_file = OWN / "actual_transport_v8.py" if selected == "CURRENT" else Path("/workspace/engineering/rcc-current396925-private-V8-source-only/actual_transport_v8.py")
    module = ast.parse(source_file.read_bytes())
    main = next(n for n in module.body if isinstance(n, ast.FunctionDef) and n.name == "main")
    guard = next(n for n in main.body if isinstance(n, ast.FunctionDef) and n.name == "guard")
    exact_ast = ast.dump(guard, include_attributes=False)
    nodes = ast.Module(body=[guard], type_ignores=[])
    bodies = {}
    modes = {}
    source_rows = []
    git_rows = []
    git_objects = {}
    native_rows = []
    source_root = "/controlled-source"
    native_root = "/controlled-native"
    for i in range(1440):
        name = f"source-{i}.py"
        body = f"controlled-source-{i}".encode()
        obj = hashlib.sha1(b"blob " + str(len(body)).encode() + b"\0" + body).hexdigest()
        bodies[source_root + "/" + name] = body
        modes[source_root + "/" + name] = 0o600
        source_rows.append(dict(path=name, mode="100644", object=obj, sha256=digest(body), fs_mode=0o600))
        git_rows.append(b"100644 blob " + obj.encode() + b"\t" + name.encode())
        git_objects[obj] = body
    for i in range(1192):
        name = f"native-{i}"
        bodies[native_root + "/" + name] = b"controlled-native"
        modes[native_root + "/" + name] = 0o600
        native_rows.append(dict(path=name, mode=0o600, kind="file", content_sha256=digest(b"controlled-native")))
    prepared = {}
    for i in range(30):
        name = f"prepared-{i}"
        bodies[source_root + "/" + name] = b"prepared"
        prepared[name] = digest(b"prepared")

    class ControlledPath:
        def __init__(self, value):
            self.value = str(value)

        def __str__(self):
            return self.value

        def __truediv__(self, child):
            return ControlledPath(self.value + "/" + str(child))

        def read_bytes(self):
            return bodies[self.value]

        def lstat(self):
            return SimpleNamespace(st_mode=stat.S_IFREG | modes[self.value])

        def is_symlink(self):
            return False

        def is_dir(self):
            return self.value in (source_root, native_root)

        def exists(self):
            return self.value in bodies

        def rglob(self, pattern):
            assert pattern == "*" and self.value == native_root
            return [ControlledPath(native_root + "/" + r["path"]) for r in native_rows]

        def relative_to(self, root):
            return Path(self.value.removeprefix(str(root) + "/"))

    def git(argv, **kwargs):
        command = argv[3:]
        if command == ["rev-parse", "HEAD"]:
            return SOURCE + "\n"
        if command == ["rev-parse", "HEAD^{tree}"]:
            return TREE + "\n"
        if command == ["status", "--porcelain"]:
            return ""
        if command == ["ls-tree", "-r", "-z", SOURCE]:
            return b"\0".join(git_rows) + b"\0"
        if command[:2] == ["cat-file", "blob"]:
            return git_objects[command[2]]
        raise AssertionError("UNEXPECTED_GIT_SEAM")

    cfg = dict(bindings=[], source_FULL={}, source_independent={}, source_FULL_independent={},
               temporal_shared_outputs=[], prepared_inputs=prepared, source_count=1440, source_body_modes=source_rows,
               native_original_root=native_root, native_original_members=native_rows)
    ns = dict(config=cfg, verify_temporal_shared_outputs=lambda rows: None, read_bound=lambda row: None, need=contracts.need, SOURCE=SOURCE, TREE=TREE,
              subprocess=SimpleNamespace(check_output=git), source_root=ControlledPath(source_root),
              root=ControlledPath("/absent-action-root"), Path=ControlledPath, content_sha=digest,
              stat=stat, os=os)
    exec(compile(nodes, str(OWN / "actual_transport_v8.py"), "exec"), ns)
    assert ast.dump(guard, include_attributes=False) == exact_ast
    action = []

    def before_action():
        ns["guard"]()
        action.append("CONTROLLED_ACTION_SENTINEL")

    before_action()
    assert action == ["CONTROLLED_ACTION_SENTINEL"]
    action.clear()
    return cfg, bodies, modes, git_rows, git_objects, before_action, action


@pytest.mark.parametrize("poison,category", [
    ("count1439", "CURRENT_COMPLETE_SOURCE_COUNT"),
    ("count_float", "CURRENT_COMPLETE_SOURCE_COUNT"),
    ("count_bool", "CURRENT_COMPLETE_SOURCE_COUNT"),
    ("old1423", "CURRENT_COMPLETE_SOURCE_COUNT"),
    ("duplicate", "CURRENT_COMPLETE_SOURCE_PATH_SET"),
    ("wrong_path", "CURRENT_COMPLETE_SOURCE_PATH_SET"),
    ("wrong_mode", "CURRENT_COMPLETE_SOURCE_GIT_MODE_OBJECT"),
    ("wrong_object", "CURRENT_COMPLETE_SOURCE_GIT_MODE_OBJECT"),
    ("wrong_git_body", "CURRENT_COMPLETE_SOURCE_GIT_BODY"),
    ("wrong_fs_body", "LIVE_SOURCE_BYTES_MODE"),
    ("wrong_fs_mode", "LIVE_SOURCE_BYTES_MODE"),
])
def test_baseline_first_actual_source_guard_rejects_before_action(poison, category):
    cfg, bodies, modes, _, objects, check, action = source_guard_case()
    row = cfg["source_body_modes"][0]
    if poison == "count1439":
        cfg["source_count"] = 1439
    elif poison == "count_float":
        cfg["source_count"] = 1440.0
    elif poison == "count_bool":
        cfg["source_count"] = True
    elif poison == "old1423":
        cfg["source_count"] = 1423
        cfg["source_body_modes"] = cfg["source_body_modes"][:1423]
    elif poison == "duplicate":
        row["path"] = cfg["source_body_modes"][1]["path"]
    elif poison == "wrong_path":
        row["path"] = "invented.py"
    elif poison == "wrong_mode":
        row["mode"] = "100755"
    elif poison == "wrong_object":
        row["object"] = "f" * 40
    elif poison == "wrong_git_body":
        objects[row["object"]] = b"altered Git body"
    elif poison == "wrong_fs_body":
        bodies["/controlled-source/" + row["path"]] = b"altered filesystem body"
    else:
        modes["/controlled-source/" + row["path"]] = 0o700
    with pytest.raises(contracts.AdmissionFailure) as error:
        check()
    assert error.value.code == category
    assert action == []


def make_alias_case(tmp_path, monkeypatch):
    original = tmp_path / "missing-original.tar.gz"
    physical = tmp_path / "physical.tar.gz"
    index = tmp_path / "original-index.json"
    mapping_path = tmp_path / "mapping.json"
    physical.write_bytes(b"owned synthetic archive body")
    index.write_bytes(b"owned synthetic index")
    physical.chmod(0o600)
    index.chmod(0o600)
    meta = physical.stat()
    expected = dict(path=str(original), bytes=meta.st_size, sha256=digest(physical.read_bytes()), mode="0o600")
    old = dict(expected, mode=0o600, uid=os.getuid(), gid=os.getgid(), mtime_ns=meta.st_mtime_ns)
    new = dict(old, path=str(physical))
    mapping = dict(schema="EXACT_ONE_HISTORICAL_COMPRESSED_ARCHIVE_PHYSICAL_ALIAS",
                   original_index_unchanged=True, failed_history="UNCHANGED_NO_ACCEPTANCE_UPGRADE",
                   original=old, new_physical=new,
                   original_index_binding=dict(path=str(index), bytes=index.stat().st_size,
                                               sha256=digest(index.read_bytes()), mode="0o600"))
    monkeypatch.setattr(alias, "TMP_ORIGINAL", expected.copy())

    def bind_mapping():
        mapping_path.write_text(json.dumps(mapping))
        mapping_path.chmod(0o600)
        monkeypatch.setattr(alias, "TMP_MAPPING", dict(path=str(mapping_path), bytes=mapping_path.stat().st_size,
                                                     sha256=digest(mapping_path.read_bytes()), mode="0o600"))

    bind_mapping()
    result = alias.verify_missing_original(expected)
    assert result["raw_body_returned"] is False
    assert result["failed_history"] == "UNCHANGED_NO_ACCEPTANCE_UPGRADE"
    return expected, mapping, bind_mapping, original, physical, index


@pytest.mark.parametrize("poison,category", [
    ("extra_key", "UNAPPROVED_TMP_ARCHIVE_ALIAS"),
    ("wrong_original_digest", "UNAPPROVED_TMP_ARCHIVE_ALIAS"),
    ("co_mutated_labels", "TMP_ALIAS_ORIGINAL_TUPLE"),
    ("changed_body", "HISTORICAL_ALIAS_BODY"),
    ("changed_mode", "HISTORICAL_ALIAS_MODE"),
    ("symlink", "HISTORICAL_ALIAS_REGULAR"),
    ("wrong_uid", "TMP_ALIAS_PHYSICAL_METADATA"),
    ("wrong_gid", "TMP_ALIAS_PHYSICAL_METADATA"),
    ("wrong_mtime", "TMP_ALIAS_PHYSICAL_METADATA"),
    ("changed_index", "HISTORICAL_ALIAS_BODY"),
    ("old_recreated", "OLD_TMP_ARCHIVE_MUST_REMAIN_ABSENT"),
    ("unknown_schema", "TMP_ALIAS_HISTORY"),
    ("history_upgrade", "TMP_ALIAS_HISTORY"),
    ("index_changed_flag", "TMP_ALIAS_HISTORY"),
])
def test_baseline_first_exact_alias_semantics_reject_poison(tmp_path, monkeypatch, poison, category):
    row, mapping, bind_mapping, original, physical, index = make_alias_case(tmp_path, monkeypatch)
    if poison == "extra_key":
        row["unknown"] = True
    elif poison == "wrong_original_digest":
        row["sha256"] = "0" * 64
    elif poison == "co_mutated_labels":
        mapping["original"]["sha256"] = mapping["new_physical"]["sha256"] = "0" * 64
        bind_mapping()
    elif poison == "changed_body":
        physical.write_bytes(b"altered")
    elif poison == "changed_mode":
        physical.chmod(0o640)
    elif poison == "symlink":
        target = physical.with_name("target")
        physical.rename(target)
        physical.symlink_to(target)
    elif poison in ("wrong_uid", "wrong_gid", "wrong_mtime"):
        key = dict(wrong_uid="uid", wrong_gid="gid", wrong_mtime="mtime_ns")[poison]
        mapping["original"][key] += 1
        mapping["new_physical"][key] += 1
        bind_mapping()
    elif poison == "changed_index":
        index.write_bytes(b"altered")
    elif poison == "old_recreated":
        original.write_bytes(physical.read_bytes())
    elif poison == "unknown_schema":
        mapping["schema"] = "UNKNOWN"
        bind_mapping()
    elif poison == "history_upgrade":
        mapping["failed_history"] = "PASS"
        bind_mapping()
    else:
        mapping["original_index_unchanged"] = False
        bind_mapping()
    with pytest.raises(contracts.AdmissionFailure) as error:
        alias.verify_missing_original(row)
    assert error.value.code == category


def test_original_failed_receipt_still_delegates_exact_row(monkeypatch):
    row = dict(path="/controlled-original-failed-row")
    calls = []
    sentinel = object()
    monkeypatch.setattr(alias, "verify_original_failed_receipt", lambda actual: calls.append(actual) or sentinel)
    assert alias.verify_missing_original(row) is sentinel
    assert calls == [row]


def test_transport_read_bound_resolves_valid_exact_original_alias(tmp_path, monkeypatch):
    import importlib.util
    selected = os.environ.get("PRIVATE_V8_COUNT_ALIAS_BASELINE", "CURRENT")
    assert selected in ("CURRENT", "ORIGINAL")
    source_file = OWN / "actual_transport_v8.py" if selected == "CURRENT" else Path("/workspace/engineering/rcc-current396925-private-V8-source-only/actual_transport_v8.py")
    spec = importlib.util.spec_from_file_location("controlled_transport_alias", source_file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    row, _, _, _, _, _ = make_alias_case(tmp_path, monkeypatch)
    if selected == "CURRENT":
        monkeypatch.setattr(module, "TMP_ORIGINAL", alias.TMP_ORIGINAL)
    assert module.read_bound(row) is None
