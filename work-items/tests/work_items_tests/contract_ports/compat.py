"""Compatibility-only setup helpers for executable upstream test bodies."""

import json
import shutil
from pathlib import Path


def direct_file_adapter(adapter_type, items_in: Path, items_out: Path):
    """Map the pinned direct-file fixture into the package directory layout."""
    input_dir = items_in.parent / "work-items-in"
    output_dir = items_out.parent / "work-items-out"
    input_dir.mkdir()
    output_dir.mkdir()

    work_items = []
    for index, item in enumerate(json.loads(items_in.read_text())):
        file_names = list(item.get("files", {}))
        work_items.append(
            {
                "id": str(index),
                "payload": item.get("payload", {}),
                "files": file_names,
            }
        )
        files_dir = input_dir / str(index + 1)
        files_dir.mkdir()
        for name, source_name in item.get("files", {}).items():
            shutil.copyfile(items_in.parent / source_name, files_dir / name)

    (input_dir / "work-items.json").write_text(json.dumps({"workItems": work_items}))
    return adapter_type(input_path=str(input_dir), output_path=str(output_dir))
