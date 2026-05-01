"""Compatibility tests for the Robocorp-style workitems module API."""

import tempfile
from pathlib import Path

from actions import workitems


def test_workitems_module_supports_robocorp_style_flow():
    """Use workitems.inputs/outputs with done/fail-style interactions."""
    with tempfile.TemporaryDirectory() as tmpdir:
        adapter = workitems.SQLiteAdapter(
            db_path=str(Path(tmpdir) / "items.db"),
            files_dir=str(Path(tmpdir) / "files"),
        )
        workitems.init(adapter)
        workitems.seed_input(payload={"name": "repo-one"})

        processed = []
        for item in workitems.inputs:
            assert item.payload == {"name": "repo-one"}
            workitems.outputs.create({"name": item.payload["name"], "processed": True})
            item.done()
            processed.append(item.id)

        assert len(processed) == 1
        assert adapter.get_queue_stats("default")["done"] == 1
        assert adapter.get_queue_stats("default_output")["pending"] == 1


def test_distribution_alias_supports_workitems_module_flow():
    """Use the underscore alias for the hyphenated distribution name."""
    from actions_work_items import workitems as aliased_workitems

    assert aliased_workitems.inputs is workitems.inputs
    assert aliased_workitems.outputs is workitems.outputs
    assert aliased_workitems.init is workitems.init
