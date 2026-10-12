"""Real directory selector controls; never install or run a Runtime consumer."""
import importlib.util
import json
import shutil
import zipfile
from pathlib import Path

import pytest

BASE = Path(__file__).parent
SPEC = importlib.util.spec_from_file_location(
    "isolated_platform_consumer_runner", BASE / "installed-consumer-runner-v5.py"
)
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)
ORIGINAL = Path("/workspace/engineering/pr221-current618-wheel-integrity-owned")
FOREIGN = ORIGINAL / "actions_runtime-1.0.3-cp312-cp312-win_amd64.whl"


def copy_pair(directory):
    directory.mkdir(mode=0o700)
    for path in runner.WHEEL.parent.iterdir():
        target = directory / path.name
        shutil.copyfile(path, target)
        target.chmod(0o600)
    return directory


def test_original_mixed_directory_rejected_by_unchanged_actual_source_selector():
    floor = runner.load("floor")
    with pytest.raises(ValueError, match=r"found 2$"):
        floor.select_runtime_wheel(ORIGINAL)
    assert not runner.ATTEMPT.exists()


def test_exact_isolated_original_linux_pair_selects_exact_cp312():
    assert runner.WHEEL.parent.stat().st_mode & 0o777 == 0o700
    assert len(list(runner.WHEEL.parent.iterdir())) == 2
    assert all(
        path.stat().st_mode & 0o777 == 0o600 for path in runner.WHEEL.parent.iterdir()
    )
    assert (
        runner.load("floor").select_runtime_wheel(runner.WHEEL.parent) == runner.WHEEL
    )
    assert runner.digest(runner.WHEEL) == runner.WHEEL_SHA


def test_foreign_cp312_original_wheel_rejected_without_platform_filter(tmp_path):
    directory = copy_pair(tmp_path / "mixed")
    assert (
        runner.load("floor").select_runtime_wheel(directory)
        == directory / runner.WHEEL.name
    )
    shutil.copyfile(FOREIGN, directory / FOREIGN.name)
    with pytest.raises(ValueError, match=r"found 2$"):
        runner.load("floor").select_runtime_wheel(directory)


@pytest.mark.parametrize(
    "field,bad",
    [
        (b"Name: actions-runtime", b"Name: unrelated"),
        (b"Version: 1.0.3", b"Version: 1.0.2"),
    ],
)
def test_real_selector_metadata_and_version_rejection_unchanged(tmp_path, field, bad):
    directory = tmp_path / "poison"
    directory.mkdir(mode=0o700)
    target = directory / runner.WHEEL.name
    with zipfile.ZipFile(runner.WHEEL) as source, zipfile.ZipFile(
        target, "w"
    ) as result:
        for member in source.infolist():
            body = source.read(member)
            if member.filename.endswith(".dist-info/METADATA"):
                assert body.count(field) == 1
                body = body.replace(field, bad)
            result.writestr(member, body)
    with pytest.raises(
        ValueError, match="Unexpected distribution|Unexpected Runtime version"
    ):
        runner.load("floor").select_runtime_wheel(directory)


def test_valid_metadata_selector_is_not_complete_pinned_wheel_identity(tmp_path):
    baseline = runner.admit_current_inputs()
    assert baseline["record_entries"] == 221
    directory = tmp_path / "renamed"
    directory.mkdir(mode=0o700)
    renamed = directory / "actions_runtime-1.0.3-cp312-cp312-unqualified_platform.whl"
    shutil.copyfile(runner.WHEEL, renamed)
    renamed.chmod(0o600)
    assert runner.digest(renamed) == runner.WHEEL_SHA
    assert runner.load("floor").select_runtime_wheel(directory) == renamed
    manifest = json.loads(runner.SOURCES["input_manifest"][0].read_text())
    with pytest.raises(AssertionError):
        runner.load("input_gate").admit(
            runner.ARCHIVE, renamed, manifest, runner.CHECKOUT
        )


def test_exact_selected_pair_and_unchanged_full_input_guard_before_freeze():
    assert (
        runner.load("floor").select_runtime_wheel(runner.WHEEL.parent) == runner.WHEEL
    )
    receipt = runner.admit_current_inputs()
    assert receipt["python_member_count"] == 202
    assert receipt["tracked_payload_source_matches"] == 215
    assert receipt["record_entries"] == 221
    assert receipt["record_verified_entries"] == 220
    assert receipt["generated_oauth_content"] == "EMPTY_CONTENT_AUTHORITY_HOLD"
    assert not runner.ATTEMPT.exists()
