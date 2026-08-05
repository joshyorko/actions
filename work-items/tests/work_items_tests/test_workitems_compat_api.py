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


def test_context_preserves_path_and_bytes_attachments():
    """Path and bytes attachments retain their contents through context helpers."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        source = root / "source.txt"
        source.write_bytes(b"from-path")
        adapter = workitems.SQLiteAdapter(
            db_path=str(root / "items.db"),
            files_dir=str(root / "files"),
        )
        context = workitems.WorkItemsContext(adapter)

        input_id = context.seed_input(
            files={"from-path.txt": source, "from-bytes.bin": b"from-bytes"}
        )
        assert adapter.get_file(input_id, "from-path.txt") == b"from-path"
        assert adapter.get_file(input_id, "from-bytes.bin") == b"from-bytes"

        context.get_input()
        output = context.create_output(
            files={"output-path.txt": source, "output-bytes.bin": b"output-bytes"}
        )
        assert output.get_file("output-path.txt") == b"from-path"
        assert output.get_file("output-bytes.bin") == b"output-bytes"
