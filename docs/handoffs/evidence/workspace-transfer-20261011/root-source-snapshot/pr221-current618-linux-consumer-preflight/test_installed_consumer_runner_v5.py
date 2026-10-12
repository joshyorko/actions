"""Service-free admission tests; none installs or imports Runtime consumer bytes."""

import hashlib
import importlib.util
import zipfile
from pathlib import Path

import pytest

PATH = Path(__file__).with_name("installed-consumer-runner-v5.py")
SPEC = importlib.util.spec_from_file_location("consumer_runner_review", PATH)
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


def fixture(tmp_path, code="from actions import ActionContext\n"):
    prefix = tmp_path / "venv"
    installed = prefix / "lib/actions/server/unimported.py"
    installed.parent.mkdir(parents=True)
    installed.write_text(code)
    wheel = tmp_path / "runtime.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr("actions/server/unimported.py", code)
    inventory = {
        "prefix": str(prefix.resolve()),
        "base_prefix": "/different-base",
        "runtime_version": "1.0.3",
        "wheel_sha256": runner.digest(wheel),
        "members": {"actions/server/unimported.py": str(installed)},
        "sys_path": [str(prefix)],
        "modules": {
            name: str(installed)
            for name in ("actions", "actions.server", "actions.mcp", "actions_http")
        },
    }
    return prefix, installed, wheel, inventory


def test_live_source_binding_passes_without_consumer_execution():
    runner.assert_source_bytes()


def test_changed_source_is_rejected(tmp_path):
    source = tmp_path / "helper.py"
    source.write_text("accepted")
    binding = {"guard": (source, hashlib.sha256(source.read_bytes()).hexdigest())}
    runner.assert_source_bytes(binding)
    source.write_text("changed")
    with pytest.raises(AssertionError, match="source bytes changed"):
        runner.assert_source_bytes(binding)


def test_exact_unimported_member_passes_existing_guard(tmp_path):
    prefix, installed, wheel, inventory = fixture(tmp_path)
    result = runner.bind_inventory(wheel, inventory, prefix, runner.load("guard"))
    assert result == [
        {
            "member": "actions/server/unimported.py",
            "path": str(installed),
            "sha256": runner.digest(installed),
        }
    ]


@pytest.mark.parametrize(
    "poison,expected",
    [
        ("missing", "inventory differs"),
        ("extra", "inventory differs"),
        ("bytes", "differs from selected wheel"),
        ("prefix", "outside the clean environment"),
        ("wheel", "selected wheel digest mismatch"),
        ("base", "fresh virtual environment"),
        ("version", ""),
    ],
)
def test_poisoned_inventory_rejected_by_actual_admission(tmp_path, poison, expected):
    prefix, installed, wheel, inventory = fixture(tmp_path)
    if poison == "missing":
        inventory["members"].clear()
    elif poison == "extra":
        inventory["members"]["extra.py"] = str(installed)
    elif poison == "bytes":
        installed.write_text("changed = True\n")
    elif poison == "prefix":
        escaped = tmp_path / "outside.py"
        escaped.write_bytes(installed.read_bytes())
        inventory["members"]["actions/server/unimported.py"] = str(escaped)
    elif poison == "wheel":
        inventory["wheel_sha256"] = "0" * 64
    elif poison == "base":
        inventory["base_prefix"] = inventory["prefix"]
    elif poison == "version":
        inventory["runtime_version"] = "1.0.2"
    with pytest.raises(AssertionError, match=expected):
        runner.bind_inventory(wheel, inventory, prefix, runner.load("guard"))


@pytest.mark.parametrize(
    "code",
    [
        "from actions._protocols import JSONValue\n",
        "import actions._managed_parameters\n",
        'import importlib\nimportlib.import_module("actions." + "_protocols")\n',
        'import importlib as importer\nimporter.import_module("actions._protocols")\n',
    ],
)
def test_full_unimported_private_core_member_rejected(tmp_path, code):
    prefix, _, wheel, inventory = fixture(tmp_path, code)
    with pytest.raises(AssertionError, match="Runtime imports Core-private modules"):
        runner.bind_inventory(wheel, inventory, prefix, runner.load("guard"))


def test_original_failure_survives_additional_cleanup_failure():
    primary = subprocess_error = RuntimeError("primary pip failure")
    with pytest.raises(RuntimeError, match="primary pip failure") as raised:
        runner.finish(primary, {"wrapper_reaped": False})
    assert raised.value is subprocess_error
    assert "Cleanup also failed" in raised.value.__notes__[0]


def test_incomplete_cleanup_cannot_pass_when_consumer_passed():
    with pytest.raises(RuntimeError, match="Owned cleanup incomplete"):
        runner.finish(None, {"status": "passed", "wrapper_reaped": False})


@pytest.mark.parametrize("poison", ["search_path", "module_origin"])
def test_checkout_or_outside_module_origin_is_rejected(tmp_path, poison):
    prefix, _, wheel, inventory = fixture(tmp_path)
    if poison == "search_path":
        inventory["sys_path"].append(str(runner.CHECKOUT))
    else:
        inventory["modules"]["actions"] = "/outside/environment/actions.py"
    with pytest.raises((AssertionError, RuntimeError)):
        runner.bind_inventory(wheel, inventory, prefix, runner.load("guard"))


@pytest.mark.parametrize("checkout", runner.CHECKOUT_ROOTS)
def test_every_known_checkout_search_path_is_rejected(tmp_path, checkout):
    prefix, _, wheel, inventory = fixture(tmp_path)
    inventory["sys_path"].append(str(checkout))
    with pytest.raises(RuntimeError, match="source checkout"):
        runner.bind_inventory(wheel, inventory, prefix, runner.load("guard"))


def test_checkout_alias_search_path_is_rejected_after_resolution(tmp_path):
    prefix, _, wheel, inventory = fixture(tmp_path)
    alias = tmp_path / "source-alias"
    alias.symlink_to(runner.CHECKOUT, target_is_directory=True)
    inventory["sys_path"].append(str(alias))
    with pytest.raises(RuntimeError, match="source checkout"):
        runner.bind_inventory(wheel, inventory, prefix, runner.load("guard"))


def test_symlinked_member_cannot_escape_owned_prefix(tmp_path):
    prefix, installed, wheel, inventory = fixture(tmp_path)
    outside = tmp_path / "escaped.py"
    outside.write_bytes(installed.read_bytes())
    # Keep loaded origins independently valid to reach the member-only guard.
    origin = prefix / "lib/public_origin.py"
    origin.write_bytes(b"public = True\n")
    inventory["modules"] = {name: str(origin) for name in inventory["modules"]}
    installed.unlink()
    installed.symlink_to(outside)
    with pytest.raises(AssertionError, match="outside the clean environment"):
        runner.bind_inventory(wheel, inventory, prefix, runner.load("guard"))


@pytest.mark.parametrize(
    "code",
    [
        "from actions import _protocols\n",
        "from importlib import import_module as loader\nloader('actions.' + '_request')\n",
        "import importlib as loader\nloader.import_module('._request', package='actions')\n",
        "from builtins import __import__ as loader\nloader('actions.' + '_request')\n",
        "import builtins as loader\nloader.__import__('actions._protocols')\n",
        "__import__('actions', fromlist=['_request'])\n",
    ],
)
def test_additional_unimported_alias_relative_and_builtin_private_core_rejected(
    tmp_path, code
):
    prefix, _, wheel, inventory = fixture(tmp_path, code)
    with pytest.raises(AssertionError, match="Runtime imports Core-private modules"):
        runner.bind_inventory(wheel, inventory, prefix, runner.load("guard"))


@pytest.mark.parametrize("poison", ["missing", "version", "url", "digest"])
def test_public_floor_report_enforces_original_public_url_sha_version(tmp_path, poison):
    import copy
    import json

    floor = runner.load("floor")
    install = [
        {
            "metadata": {"name": name, "version": value["version"]},
            "download_info": {
                "url": value["url"],
                "archive_info": {"hashes": {"sha256": value["sha256"]}},
            },
        }
        for name, value in floor.EXPECTED_PUBLIC_PACKAGES.items()
    ]
    report = tmp_path / "report.json"
    report.write_text(json.dumps({"install": install}))
    assert floor.verify_public_package_report(report) == floor.EXPECTED_PUBLIC_PACKAGES
    bad = copy.deepcopy(install)
    if poison == "missing":
        bad.pop()
    elif poison == "version":
        bad[0]["metadata"]["version"] = "99.0.0"
    elif poison == "url":
        bad[0]["download_info"]["url"] = "https://example.invalid/not-public.whl"
    else:
        bad[0]["download_info"]["archive_info"]["hashes"]["sha256"] = "0" * 64
    report.write_text(json.dumps({"install": bad}))
    with pytest.raises(RuntimeError):
        floor.verify_public_package_report(report)


@pytest.mark.parametrize(
    "field",
    [
        "wrapper_reaped",
        "descendant_snapshot_complete",
        "descendant_reap_complete",
        "temporary_removed",
        "cleanup_errors",
        "active_readers",
        "observed_live_children",
        "observed_zombie_children",
    ],
)
def test_every_missing_cleanup_predicate_prevents_acceptance(field):
    complete = {
        name: True
        for name in [
            "wrapper_reaped",
            "descendant_snapshot_complete",
            "descendant_reap_complete",
            "temporary_removed",
        ]
    }
    complete.update(
        {
            name: []
            for name in [
                "cleanup_errors",
                "active_readers",
                "observed_live_children",
                "observed_zombie_children",
            ]
        }
    )
    assert runner.cleanup_is_complete(complete)
    complete.pop(field)
    assert not runner.cleanup_is_complete(complete)
    with pytest.raises(RuntimeError, match="Owned cleanup incomplete"):
        runner.finish(None, complete)
