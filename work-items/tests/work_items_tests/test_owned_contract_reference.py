"""Immutable-object authentication and unchanged semantic-authority parity."""

import base64
import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

PACKAGE = Path(__file__).resolve().parents[2]


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def checker(tmp_path):
    root = tmp_path / "work-items"
    for relative in (
        "scripts",
        "contracts",
        "tests/contract_sources",
        "tests/work_items_tests/contract_ports",
    ):
        destination = root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(PACKAGE / relative, destination)
    return load(root / "scripts/check_contract_port_provenance.py", "candidate_checker")


def ref(checker):
    return checker.ROOT / "contracts/references/robocorp-1.5.0"


def pin(checker):
    return json.loads(checker.MANIFEST_PATH.read_text())["sources"]["robocorp-1.5.0"]["commit"]


def test_offline_authenticated_reference_no_git_or_network(checker, monkeypatch):
    monkeypatch.setattr(checker.subprocess, "run", lambda *a, **k: pytest.fail("Git prohibited"))
    root = checker._verify_robocorp_reference(ref(checker), pin(checker))
    assert len([p for p in root.rglob("*") if p.is_file()]) == 17
    assert "Apache License" in (root / "LICENSE").read_text()


@pytest.mark.parametrize(
    "damage",
    [
        "commit",
        "tree",
        "blob",
        "license",
        "missing",
        "extra",
        "traversal",
        "symlink",
        "inventory",
        "proof-extra",
    ],
)
def test_reference_tampering_rejected(checker, damage):
    root = ref(checker)
    if damage in ("commit", "tree", "traversal", "proof-extra"):
        p = root / "object-proof.json"
        value = json.loads(p.read_text())
        if damage == "commit":
            value["commit_base64"] = base64.b64encode(b"forged").decode()
        elif damage == "tree":
            value["trees"][""]["base64"] = base64.b64encode(b"forged").decode()
        elif damage == "traversal":
            value["trees"]["../outside"] = value["trees"][""]
        else:
            value["trees"]["unreferenced"] = value["trees"][""]
        p.write_text(json.dumps(value))
    elif damage == "inventory":
        p = root / "inventory.json"
        value = json.loads(p.read_text())
        value[0]["sha256"] = "0" * 64
        p.write_text(json.dumps(value))
    elif damage == "extra":
        (root / "payload/workitems/src/robocorp/workitems/_extra.py").write_text(
            "def Input(): pass\n"
        )
    else:
        p = (
            root / "payload/LICENSE"
            if damage == "license"
            else root / "payload/workitems/tests/workitems_tests/test_email.py"
        )
        if damage == "missing":
            p.unlink()
        elif damage == "symlink":
            data = p.read_bytes()
            p.unlink()
            target = root.parent / "outside"
            target.write_bytes(data)
            p.symlink_to(target)
        else:
            raw = bytearray(p.read_bytes())
            raw[-1] ^= 1
            p.write_bytes(raw)
    with pytest.raises((ValueError, KeyError)):
        checker._verify_robocorp_reference(root, pin(checker))


def custom_fixture(checker, monkeypatch):
    # Existing owned snapshots supply synthetic custom-root semantics; no new
    # custom-source distribution. Only its public surface is mocked here.
    manifest = json.loads(checker.MANIFEST_PATH.read_text())
    custom = checker.ROOT.parent / "custom"
    tests = custom / "workitems_tests"
    tests.mkdir(parents=True)
    shutil.copyfile(
        checker.ROOT / manifest["sources"]["custom-0.1.6"]["ports"]["test_adapters.py"]["source"],
        tests / "test_adapters.py",
    )
    for name, snapshot in checker.REFERENCE_AUXILIARY["custom-0.1.6"].items():
        shutil.copyfile(snapshot, tests / name)
    (tests / "test_fizzy_orchestration.py").touch()
    package = custom / "robocorp_adapters_custom"
    package.mkdir()
    (package / "_yorko_control_room.py").touch()
    original = checker._verify_public_surface

    def check(origin, *args):
        if origin == "robocorp-1.5.0":
            original(origin, *args)

    monkeypatch.setattr(checker, "_verify_public_surface", check)
    return custom


def test_semantic_parity_with_git_root_mode_and_custom_still_required(checker, monkeypatch):
    manifest = json.loads(checker.MANIFEST_PATH.read_text())
    robocorp = ref(checker) / "payload"
    custom = custom_fixture(checker, monkeypatch)

    def expected(root):
        return manifest["sources"]["custom-0.1.6" if root == custom else "robocorp-1.5.0"]["commit"]

    monkeypatch.setattr(checker, "_git_head", expected)
    checker._verify_authoritative(robocorp, custom)
    seen = []

    def custom_only(root):
        seen.append(root)
        assert root == custom
        return expected(root)

    monkeypatch.setattr(checker, "_git_head", custom_only)
    checker._verify_authoritative(ref(checker), custom, robocorp_reference=True)
    assert seen == [custom]
    monkeypatch.setattr(checker, "_git_head", lambda root: "0" * 40)
    with pytest.raises(SystemExit, match="custom adapter reference HEAD"):
        checker._verify_authoritative(ref(checker), custom, robocorp_reference=True)


@pytest.mark.parametrize("damage", ["assertion", "decorator", "fixture", "public-export"])
def test_existing_semantic_guards_still_reject(checker, monkeypatch, damage):
    manifest = json.loads(checker.MANIFEST_PATH.read_text())
    custom = custom_fixture(checker, monkeypatch)
    monkeypatch.setattr(
        checker, "_git_head", lambda root: manifest["sources"]["custom-0.1.6"]["commit"]
    )
    if damage == "public-export":
        p = checker.LEDGER_PATH
        value = json.loads(p.read_text())
        value["public_surfaces"]["robocorp-1.5.0"]["symbols"].append("forged_export")
        p.write_text(json.dumps(value))
    else:
        p = (
            checker.ROOT
            / manifest["sources"]["robocorp-1.5.0"]["ports"]["test_adapters.py"]["adapted"]
        )
        text = p.read_text()
        if damage == "assertion":
            text = text.replace("assert ", "assert False and ", 1)
        elif damage == "decorator":
            text = text.replace(
                "class TestFileAdapter:", "@pytest.mark.skip\nclass TestFileAdapter:"
            )
        else:
            text = text.replace(
                "def adapter(self,", "def adapter(self, unexpected_required_fixture,", 1
            )
        assert text != p.read_text(), "tamper fixture must alter source"
        p.write_text(text)
    with pytest.raises((SystemExit, AssertionError)):
        checker._verify_authoritative(ref(checker), custom, robocorp_reference=True)


@pytest.mark.parametrize(
    "arguments",
    [
        ["--robocorp-reference", "missing"],
        ["--custom-root", "missing"],
        [
            "--robocorp-reference",
            "missing",
            "--robocorp-root",
            "missing",
            "--custom-root",
            "missing",
        ],
        ["--robocorp-reference", "missing", "--custom-root", "missing", "--write"],
    ],
)
def test_invalid_cli_modes_fail_before_reference_reads(checker, arguments):
    result = subprocess.run(
        [
            sys.executable,
            str(checker.ROOT / "scripts/check_contract_port_provenance.py"),
            *arguments,
        ],
        capture_output=True,
    )
    assert result.returncode == 2
