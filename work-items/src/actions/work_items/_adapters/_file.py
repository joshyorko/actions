"""
File-based adapter for work items.

Stores work items in JSON files compatible with Robocorp Control Room
format. This adapter is useful for local development and testing.

Based on robocorp-workitems (Apache 2.0 License).
"""

import json
import logging
import os
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from .._exceptions import EmptyQueue
from .._paths import resolve_attachment_path, resolve_item_directory
from .._types import ExceptionType, JSONType, State
from ._base import BaseAdapter

log = logging.getLogger(__name__)


class FileAdapter(BaseAdapter):
    """
    File-based work item adapter using JSON files.

    Compatible with Robocorp Control Room work item format:
    - Input items: {input_path}/work-items.json
    - Output items: {output_path}/work-items.json
    - Files stored alongside in numbered directories

    Directory structure:
        work-items-in/
            work-items.json
            1/
                file1.txt
            2/
                file2.pdf
        work-items-out/
            work-items.json
            1/
                output1.csv

    Environment variables:
        RC_WORKITEM_INPUT_PATH: Input directory (default: ./output/work-items-in)
        RC_WORKITEM_OUTPUT_PATH: Output directory (default: ./output/work-items-out)
    """

    def __new__(
        cls,
        input_path: str | None = None,
        output_path: str | None = None,
    ):
        if cls is FileAdapter:
            raw_input = (
                input_path
                or os.environ.get("RC_WORKITEM_INPUT_PATH")
                or os.environ.get("RPA_INPUT_WORKITEM_PATH")
            )
            raw_output = (
                output_path
                or os.environ.get("RC_WORKITEM_OUTPUT_PATH")
                or os.environ.get("RPA_OUTPUT_WORKITEM_PATH")
            )
            candidates = (
                Path(raw_input) if raw_input else None,
                Path(raw_output) if raw_output else None,
            )
            if any(
                candidate is not None
                and (
                    candidate.is_file()
                    or (not candidate.exists() and candidate.suffix.lower() == ".json")
                )
                for candidate in candidates
            ):
                return _DirectFileAdapter(raw_input, raw_output)
        return super().__new__(cls)

    def __init__(
        self,
        input_path: str | None = None,
        output_path: str | None = None,
    ):
        """
        Initialize file adapter.

        Args:
            input_path: Directory containing input work items.
            output_path: Directory for output work items.
        """
        self._input_path = Path(
            input_path
            or os.environ.get("RC_WORKITEM_INPUT_PATH")
            or os.environ.get("RPA_INPUT_WORKITEM_PATH")
            or "./output/work-items-in"
        )
        self._output_path = Path(
            output_path
            or os.environ.get("RC_WORKITEM_OUTPUT_PATH")
            or os.environ.get("RPA_OUTPUT_WORKITEM_PATH")
            or "./output/work-items-out"
        )

        # Ensure directories exist
        self._input_path.mkdir(parents=True, exist_ok=True)
        self._output_path.mkdir(parents=True, exist_ok=True)

        # Load or initialize work items
        self._input_items = self._load_items(self._input_path)
        self._output_items = self._load_items(self._output_path)

        # Track reservation state
        self._reserved: dict[str, bool] = {}
        self._current_index = 0

    def _load_items(self, path: Path) -> list[dict[str, Any]]:
        """Load work items from JSON file."""
        items_file = path / "work-items.json"
        if items_file.exists():
            with open(items_file) as f:
                data = json.load(f)
                return data.get("workItems", data.get("items", []))
        return []

    def _save_items(self, path: Path, items: list[dict[str, Any]]) -> None:
        """Save work items to JSON file."""
        items_file = path / "work-items.json"
        with open(items_file, "w") as f:
            json.dump({"workItems": items}, f, indent=2, default=str)

    def _get_files_dir(self, path: Path, index: int) -> Path:
        """Get directory for work item files."""
        files_dir = resolve_item_directory(path, str(index + 1))
        files_dir.mkdir(parents=True, exist_ok=True)
        return files_dir

    def _validate_item_id(self, item_id: str) -> None:
        resolve_item_directory(self._input_path, item_id)

    def _find_item_index(self, items: list[dict], item_id: str) -> int:
        """Find item index by ID."""
        self._validate_item_id(item_id)
        for i, item in enumerate(items):
            if item.get("id") == item_id:
                return i
        raise ValueError(f"Work item not found: {item_id}")

    def reserve_input(self) -> str:
        """Reserve next available input work item."""
        while self._current_index < len(self._input_items):
            item = self._input_items[self._current_index]
            item_id = item.get("id", str(self._current_index))

            # Ensure item has ID
            if "id" not in item:
                item["id"] = item_id
                self._save_items(self._input_path, self._input_items)

            if not self._reserved.get(item_id):
                self._reserved[item_id] = True
                self._current_index += 1
                log.debug(f"Reserved input work item: {item_id}")
                return item_id

            self._current_index += 1

        raise EmptyQueue("No more input work items available")

    def release_input(
        self,
        item_id: str,
        state: State,
        exception_type: ExceptionType | dict[str, Any] | None = None,
        code: str | None = None,
        message: str | None = None,
        exception: dict[str, Any] | None = None,
    ) -> None:
        """Release a reserved input work item."""
        try:
            if exception is not None:
                if exception_type is not None or code is not None or message is not None:
                    raise TypeError("release_input() received both exception and split exception fields")
                exception_type = exception
            index = self._find_item_index(self._input_items, item_id)
            item = self._input_items[index]

            item["state"] = state.value
            if isinstance(exception_type, dict):
                exception = dict(exception_type)
                exception_kind = exception.get("type")
                if isinstance(exception_kind, ExceptionType):
                    exception["type"] = exception_kind.value
                item["exception"] = exception
            elif exception_type:
                item["exception"] = {
                    "type": exception_type.value,
                    "code": code,
                    "message": message,
                }

            self._save_items(self._input_path, self._input_items)
            log.debug(f"Released input work item {item_id} with state {state.value}")
        except ValueError:
            log.warning(f"Could not find input item to release: {item_id}")

    def create_output(
        self,
        parent_id: str,
        payload: JSONType | None = None,
    ) -> str:
        """Create a new output work item."""
        item_id = str(uuid.uuid4())

        item = {
            "id": item_id,
            "payload": payload or {},
            "files": [],
            "parentId": parent_id,
            "state": State.PENDING.value,
            "createdAt": datetime.utcnow().isoformat(),
        }

        self._output_items.append(item)
        self._save_items(self._output_path, self._output_items)

        log.debug(f"Created output work item: {item_id}")
        return item_id

    def load_payload(self, item_id: str) -> JSONType:
        """Load payload from work item."""
        # Check inputs first
        for item in self._input_items:
            if item.get("id") == item_id:
                return item.get("payload", {})

        # Then check outputs
        for item in self._output_items:
            if item.get("id") == item_id:
                return item.get("payload", {})

        raise ValueError(f"Work item not found: {item_id}")

    def save_payload(self, item_id: str, payload: JSONType) -> None:
        """Save payload to work item."""
        # Check inputs
        for item in self._input_items:
            if item.get("id") == item_id:
                item["payload"] = payload
                self._save_items(self._input_path, self._input_items)
                return

        # Check outputs
        for item in self._output_items:
            if item.get("id") == item_id:
                item["payload"] = payload
                self._save_items(self._output_path, self._output_items)
                return

        raise ValueError(f"Work item not found: {item_id}")

    def list_files(self, item_id: str) -> list[str]:
        """List files attached to work item."""
        self._validate_item_id(item_id)
        # Check inputs
        for i, item in enumerate(self._input_items):
            if item.get("id") == item_id:
                files_dir = self._get_files_dir(self._input_path, i)
                if files_dir.exists():
                    return [
                        f.name
                        for f in files_dir.iterdir()
                        if f.is_file() and resolve_attachment_path(files_dir, f.name)
                    ]
                return item.get("files", [])

        # Check outputs
        for i, item in enumerate(self._output_items):
            if item.get("id") == item_id:
                files_dir = self._get_files_dir(self._output_path, i)
                if files_dir.exists():
                    return [
                        f.name
                        for f in files_dir.iterdir()
                        if f.is_file() and resolve_attachment_path(files_dir, f.name)
                    ]
                return item.get("files", [])

        raise ValueError(f"Work item not found: {item_id}")

    def get_file(self, item_id: str, name: str) -> bytes:
        """Get file content from work item."""
        self._validate_item_id(item_id)
        # Check inputs
        for i, item in enumerate(self._input_items):
            if item.get("id") == item_id:
                file_path = resolve_attachment_path(self._get_files_dir(self._input_path, i), name)
                if file_path.exists():
                    return file_path.read_bytes()
                raise ValueError(f"File not found: {name}")

        # Check outputs
        for i, item in enumerate(self._output_items):
            if item.get("id") == item_id:
                file_path = resolve_attachment_path(self._get_files_dir(self._output_path, i), name)
                if file_path.exists():
                    return file_path.read_bytes()
                raise ValueError(f"File not found: {name}")

        raise ValueError(f"Work item not found: {item_id}")

    def add_file(
        self,
        item_id: str,
        name: str,
        original_name: str | bytes | bytearray | None = None,
        content: bytes | None = None,
    ) -> None:
        """Add file to work item."""
        if isinstance(original_name, bytes | bytearray):
            if content is not None:
                raise TypeError(
                    "add_file received unexpected argument combination; "
                    "use signature (item_id, name, original_name, content)"
                )
            content = bytes(original_name)
            original_name = name
        if content is None:
            raise TypeError("File content is required")
        self._validate_item_id(item_id)
        # Check inputs
        for i, item in enumerate(self._input_items):
            if item.get("id") == item_id:
                file_path = resolve_attachment_path(self._get_files_dir(self._input_path, i), name)
                file_path.write_bytes(content)
                if "files" not in item:
                    item["files"] = []
                if name not in item["files"]:
                    item["files"].append(name)
                self._save_items(self._input_path, self._input_items)
                return

        # Check outputs
        for i, item in enumerate(self._output_items):
            if item.get("id") == item_id:
                file_path = resolve_attachment_path(self._get_files_dir(self._output_path, i), name)
                file_path.write_bytes(content)
                if "files" not in item:
                    item["files"] = []
                if name not in item["files"]:
                    item["files"].append(name)
                self._save_items(self._output_path, self._output_items)
                return

        raise ValueError(f"Work item not found: {item_id}")

    def remove_file(self, item_id: str, name: str) -> None:
        """Remove file from work item."""
        self._validate_item_id(item_id)
        # Check inputs
        for i, item in enumerate(self._input_items):
            if item.get("id") == item_id:
                file_path = resolve_attachment_path(self._get_files_dir(self._input_path, i), name)
                if file_path.exists():
                    file_path.unlink()
                if "files" in item and name in item["files"]:
                    item["files"].remove(name)
                self._save_items(self._input_path, self._input_items)
                return

        # Check outputs
        for i, item in enumerate(self._output_items):
            if item.get("id") == item_id:
                file_path = resolve_attachment_path(self._get_files_dir(self._output_path, i), name)
                if file_path.exists():
                    file_path.unlink()
                if "files" in item and name in item["files"]:
                    item["files"].remove(name)
                self._save_items(self._output_path, self._output_items)
                return

        raise ValueError(f"Work item not found: {item_id}")

    # Extended methods

    def seed_input(
        self,
        payload: JSONType | None = None,
        files: dict[str, bytes] | None = None,
        queue_name: str | None = None,
    ) -> str:
        """Seed a new input work item."""
        item_id = str(uuid.uuid4())
        index = len(self._input_items)

        item = {
            "id": item_id,
            "payload": payload or {},
            "files": [],
            "state": State.PENDING.value,
            "createdAt": datetime.utcnow().isoformat(),
        }

        self._input_items.append(item)

        # Add files if provided
        if files:
            files_dir = self._get_files_dir(self._input_path, index)
            for name, content in files.items():
                resolve_attachment_path(files_dir, name).write_bytes(content)
                item["files"].append(name)

        self._save_items(self._input_path, self._input_items)

        log.debug(f"Seeded input work item: {item_id}")
        return item_id

    def list_items(
        self,
        queue_name: str | None = None,
        state: State | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """List work items."""
        items = self._input_items + self._output_items

        if state:
            items = [i for i in items if i.get("state") == state.value]

        return items[:limit]

    def get_item(self, item_id: str) -> dict[str, Any]:
        """Get work item details."""
        self._validate_item_id(item_id)
        for item in self._input_items:
            if item.get("id") == item_id:
                return item

        for item in self._output_items:
            if item.get("id") == item_id:
                return item

        raise ValueError(f"Work item not found: {item_id}")

    def delete_item(self, item_id: str) -> None:
        """Delete a work item."""
        self._validate_item_id(item_id)
        # Check inputs
        for i, item in enumerate(self._input_items):
            if item.get("id") == item_id:
                files_dir = self._get_files_dir(self._input_path, i)
                if files_dir.exists():
                    shutil.rmtree(files_dir)
                self._input_items.pop(i)
                self._save_items(self._input_path, self._input_items)
                return

        # Check outputs
        for i, item in enumerate(self._output_items):
            if item.get("id") == item_id:
                files_dir = self._get_files_dir(self._output_path, i)
                if files_dir.exists():
                    shutil.rmtree(files_dir)
                self._output_items.pop(i)
                self._save_items(self._output_path, self._output_items)
                return

        raise ValueError(f"Work item not found: {item_id}")

    def get_queue_stats(self, queue_name: str | None = None) -> dict[str, int]:
        """Get queue statistics."""
        all_items = self._input_items + self._output_items

        pending = sum(1 for i in all_items if i.get("state") == State.PENDING.value)
        in_progress = sum(1 for i in all_items if i.get("state") == State.IN_PROGRESS.value)
        done = sum(1 for i in all_items if i.get("state") == State.DONE.value)
        failed = sum(1 for i in all_items if i.get("state") == State.FAILED.value)

        return {
            "pending": pending,
            "in_progress": in_progress,
            "done": done,
            "failed": failed,
            "total": len(all_items),
        }


class _DirectFileAdapter(BaseAdapter):
    """Robocorp-compatible top-level-list JSON adapter."""

    def __init__(self, input_path: str | None, output_path: str | None):
        if not input_path:
            artifacts = Path(os.environ.get("ROBOT_ARTIFACTS") or "output")
            generated_input = artifacts / "work-items-in" / "workitems.json"
            generated_input.parent.mkdir(parents=True, exist_ok=True)
            if not generated_input.exists():
                self._save(generated_input, [{"payload": None, "files": {}}])
            input_path = str(generated_input)
        self._input_path = Path(input_path).expanduser().resolve()
        self._output_path = (
            Path(output_path or self._input_path.with_name("work-items-out.json"))
            .expanduser()
            .resolve()
        )
        self._inputs = self._load(self._input_path, required=True)
        self._outputs = self._load(self._output_path, required=False)
        self._index = 0
        self._releases: dict[str, tuple[State, dict[str, Any] | None]] = {}

    @staticmethod
    def _load(path: Path, *, required: bool) -> list[dict[str, Any]]:
        if not path.exists():
            if required:
                raise ValueError(f"Invalid work items file {path}: file does not exist")
            return []
        try:
            text = path.read_text(encoding="utf-8")
            if not text.strip():
                raise ValueError("file is empty")
            data = json.loads(text)
            if not isinstance(data, list):
                raise ValueError("expected a top-level list")
            if any(not isinstance(item, dict) for item in data):
                raise ValueError("every work item must be an object")
            if required and not data:
                raise ValueError("expected at least one work item")
            return data
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            raise ValueError(f"Invalid work items file {path}: {exc}") from exc

    @staticmethod
    def _save(path: Path, items: list[dict[str, Any]]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(items, indent=2, default=str), encoding="utf-8")

    def _get_item(self, item_id: str) -> tuple[str, dict[str, Any]]:
        try:
            index = int(item_id)
        except ValueError as exc:
            raise ValueError(f"Unknown work item ID: {item_id}") from exc
        if 0 <= index < len(self._inputs):
            return "input", self._inputs[index]
        output_index = index - len(self._inputs)
        if 0 <= output_index < len(self._outputs):
            return "output", self._outputs[output_index]
        raise ValueError(f"Unknown work item ID: {item_id}")

    def _save_source(self, source: str) -> None:
        if source == "input":
            self._save(self._input_path, self._inputs)
        else:
            self._save(self._output_path, self._outputs)

    def _attachment(self, source: str, item: dict[str, Any], name: str) -> Path:
        files = item.get("files", {})
        if not isinstance(files, dict) or name not in files:
            raise ValueError(f"File not found: {name}")
        reference = Path(str(files[name]))
        if reference.is_absolute():
            raise ValueError(f"Unsafe absolute attachment path: {reference}")
        root = self._input_path.parent if source == "input" else self._output_path.parent
        candidate = (root / reference).resolve()
        if candidate == root or root not in candidate.parents:
            raise ValueError(f"Unsafe attachment path: {reference}")
        return candidate

    def reserve_input(self) -> str:
        if self._index >= len(self._inputs):
            raise EmptyQueue("No work items in the input queue")
        item_id = str(self._index)
        self._index += 1
        return item_id

    def release_input(
        self,
        item_id: str,
        state: State,
        exception_type: ExceptionType | dict[str, Any] | None = None,
        code: str | None = None,
        message: str | None = None,
    ) -> None:
        source, _ = self._get_item(item_id)
        if source != "input":
            raise ValueError(f"Work item is not an input: {item_id}")
        if item_id in self._releases:
            raise ValueError("Work item already released")
        if isinstance(exception_type, dict):
            exception = exception_type
        elif exception_type is not None:
            exception = {"type": exception_type.value, "code": code, "message": message}
        else:
            exception = None
        self._releases[item_id] = (state, exception)

    def create_output(self, parent_id: str, payload: JSONType | None = None) -> str:
        source, _ = self._get_item(parent_id)
        if source != "input" or parent_id in self._releases:
            raise ValueError(f"Invalid output parent: {parent_id}")
        self._outputs.append({"payload": payload, "files": {}})
        self._save(self._output_path, self._outputs)
        return str(len(self._inputs) + len(self._outputs) - 1)

    def load_payload(self, item_id: str) -> JSONType:
        return self._get_item(item_id)[1].get("payload")

    def save_payload(self, item_id: str, payload: JSONType) -> None:
        source, item = self._get_item(item_id)
        item["payload"] = payload
        self._save_source(source)

    def list_files(self, item_id: str) -> list[str]:
        files = self._get_item(item_id)[1].get("files", {})
        if not isinstance(files, dict):
            raise ValueError(f"Invalid files mapping for work item {item_id}")
        return list(files)

    def get_file(self, item_id: str, name: str) -> bytes:
        source, item = self._get_item(item_id)
        path = self._attachment(source, item, name)
        try:
            return path.read_bytes()
        except OSError as exc:
            raise ValueError(f"File not found: {name}") from exc

    def add_file(
        self,
        item_id: str,
        name: str,
        original_name: str | bytes | bytearray | None = None,
        content: bytes | None = None,
    ) -> None:
        if isinstance(original_name, bytes | bytearray):
            if content is not None:
                raise TypeError(
                    "add_file received unexpected argument combination; "
                    "use signature (item_id, name, original_name, content)"
                )
            content = bytes(original_name)
            original_name = name
        if content is None:
            raise TypeError("File content is required")
        source, item = self._get_item(item_id)
        root = self._input_path.parent if source == "input" else self._output_path.parent
        path = resolve_attachment_path(root, name)
        if path.exists():
            raise FileExistsError(name)
        path.write_bytes(content)
        files = item.setdefault("files", {})
        if not isinstance(files, dict):
            raise ValueError(f"Invalid files mapping for work item {item_id}")
        files[name] = name
        self._save_source(source)

    def remove_file(self, item_id: str, name: str) -> None:
        source, item = self._get_item(item_id)
        files = item.get("files", {})
        if not isinstance(files, dict) or name not in files:
            raise ValueError(f"File not found: {name}")
        del files[name]
        self._save_source(source)

    def seed_input(
        self,
        payload: JSONType | None = None,
        files: dict[str, bytes] | None = None,
        queue_name: str | None = None,
    ) -> str:
        item: dict[str, Any] = {"payload": payload, "files": {}}
        self._inputs.append(item)
        item_id = str(len(self._inputs) - 1)
        for name, content in (files or {}).items():
            self.add_file(item_id, name, name, content)
        self._save(self._input_path, self._inputs)
        return item_id

    def list_items(
        self,
        queue_name: str | None = None,
        state: State | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        return (self._inputs + self._outputs)[:limit]

    def get_item(self, item_id: str) -> dict[str, Any]:
        return self._get_item(item_id)[1]

    def delete_item(self, item_id: str) -> None:
        source, item = self._get_item(item_id)
        collection = self._inputs if source == "input" else self._outputs
        collection.remove(item)
        self._save_source(source)

    def get_queue_stats(self, queue_name: str | None = None) -> dict[str, int]:
        total = len(self._inputs) + len(self._outputs)
        return {"pending": total, "in_progress": 0, "done": 0, "failed": 0, "total": total}
