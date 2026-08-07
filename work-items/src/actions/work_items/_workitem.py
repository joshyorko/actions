"""Runtime work item containers.

Lifecycle and attachment behavior is derived from robocorp-workitems 1.5.0
(Apache-2.0) while retaining the actions-work-items adapter contract.
"""

import asyncio
import fnmatch
import json
import logging
import os
import threading
import warnings
from contextvars import ContextVar
from dataclasses import dataclass, replace
from glob import glob
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ._exceptions import ApplicationException, BusinessException, to_exception_type
from ._support import add_file as adapter_add_file
from ._support import release_input
from ._types import Email, ExceptionType, JSONType, PathType, State
from ._utils import truncate

if TYPE_CHECKING:
    from ._adapters._base import RuntimeAdapter

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class _InputState:
    state: State | None = None
    exception: dict[str, Any] | None = None
    outputs: tuple["Output", ...] = ()


class WorkItem:
    def __init__(
        self,
        adapter: "RuntimeAdapter",
        item_id: str | None = None,
        payload: JSONType = None,
        parent_id: str | None = None,
    ):
        self._adapter = adapter
        self._id = item_id
        self._parent_id = parent_id
        self._payload = payload
        self._files: list[str] = []
        self._files_to_add: dict[str, tuple[str, Path | bytes]] = {}
        self._files_to_remove: set[str] = set()
        self._saved = False

    @property
    def id(self) -> str | None:
        return self._id

    @property
    def parent_id(self) -> str | None:
        return self._parent_id

    @property
    def payload(self) -> JSONType:
        return self._payload

    @payload.setter
    def payload(self, value: JSONType) -> None:
        self._payload = value
        self._saved = False

    @property
    def files(self) -> list[str]:
        return list(self._files)

    @property
    def saved(self) -> bool:
        return self._saved

    def load(self) -> None:
        if self.id is None:
            raise RuntimeError("Unable to load unsaved item")
        self._payload = self._adapter.load_payload(self.id)
        self._files = sorted(self._adapter.list_files(self.id))
        self._saved = True

    def save(self) -> None:
        if self.id is not None:
            self._adapter.save_payload(self.id, self.payload)
        elif self.parent_id is not None:
            self._id = self._adapter.create_output(self.parent_id, self.payload)
        else:
            raise RuntimeError("Invalid work item state (no id or parent_id)")

        assert self.id is not None
        for name, (original_name, source) in self._files_to_add.items():
            content = source if isinstance(source, bytes) else source.read_bytes()
            adapter_add_file(self._adapter, self.id, name, original_name, content)
        for name in self._files_to_remove:
            self._adapter.remove_file(self.id, name)

        self._files = sorted(
            set(self._files).difference(self._files_to_remove).union(self._files_to_add)
        )
        self._files_to_add.clear()
        self._files_to_remove.clear()
        self._saved = True

    def add_file(
        self,
        path: PathType | None = None,
        name: str | None = None,
        content: bytes | None = None,
        original_name: str | None = None,
    ) -> Path | None:
        if path is not None:
            resolved = Path(path).resolve()
            if not resolved.is_file():
                raise FileNotFoundError(f"Not a valid file: {resolved}")
            name = name or resolved.name
            source: Path | bytes = resolved if content is None else content
        elif content is not None:
            if name is None:
                raise ValueError("name must be provided when using content")
            source = content
            resolved = None
        else:
            raise ValueError("Either path or content must be provided")

        self._saved = False
        self._files_to_add[name] = (original_name or name, source)
        return resolved

    def add_files(self, pattern: PathType) -> list[Path]:
        paths = []
        for match in glob(str(pattern), recursive=False):
            path = self.add_file(match)
            if path is not None:
                paths.append(path)
        return paths

    def remove_file(self, name: str, missing_ok: bool = False) -> None:
        if name not in self._files:
            if missing_ok:
                return
            raise FileNotFoundError(f"No such file in work item: {name}")
        self._files_to_remove.add(name)
        self._saved = False

    def remove_files(self, pattern: str, missing_ok: bool = True) -> list[str]:
        names = [name for name in self._files if fnmatch.fnmatch(name, pattern)]
        for name in names:
            self.remove_file(name)
        return names

    def list_files(self) -> list[str]:
        return self.files

    def get_file(self, name: str) -> bytes:
        staged = self._files_to_add.get(name)
        pending = staged[1] if staged is not None else None
        if pending is not None:
            return pending if isinstance(pending, bytes) else pending.read_bytes()
        if self.id is None:
            raise FileNotFoundError(f"No file with name: {name}")
        try:
            return self._adapter.get_file(self.id, name)
        except KeyError as err:
            raise FileNotFoundError(f"No file with name: {name}") from err


class Input(WorkItem):
    def __init__(self, adapter: "RuntimeAdapter", item_id: str, payload: JSONType = None):
        super().__init__(adapter, item_id=item_id, payload=payload)
        self._lifecycle: ContextVar[tuple[object, _InputState] | None] = ContextVar(
            f"actions_work_items_input_state_{id(self)}", default=None
        )

    @staticmethod
    def _owner() -> object:
        try:
            task = asyncio.current_task()
        except RuntimeError:
            task = None
        return task if task is not None else threading.current_thread()

    def _get_lifecycle(self) -> _InputState:
        stored = self._lifecycle.get()
        owner = self._owner()
        if stored is None or stored[0] is not owner:
            state = _InputState()
            self._lifecycle.set((owner, state))
            return state
        return stored[1]

    def _set_lifecycle(self, state: _InputState) -> None:
        self._lifecycle.set((self._owner(), state))

    def __repr__(self) -> str:
        payload = truncate(json.dumps(self.payload), 64)
        return f"Input[id={self.id},payload={payload},files={self.files},state={self.state},saved={self.saved}]"

    def __enter__(self) -> "Input":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> bool:
        if self.released:
            return False
        if exc_type is None:
            self.done()
            return False
        exception_type = to_exception_type(exc_type)
        code = getattr(exc_value, "code", None)
        message = getattr(exc_value, "message", str(exc_value))
        self.fail(exception_type, code, message)
        return issubclass(exc_type, ApplicationException | BusinessException)

    @property
    def state(self) -> State | None:
        return self._get_lifecycle().state

    @property
    def exception(self) -> dict[str, Any] | None:
        return self._get_lifecycle().exception

    @property
    def released(self) -> bool:
        return self.state is not None

    @property
    def outputs(self) -> list["Output"]:
        return list(self._get_lifecycle().outputs)

    def email(self, html: bool = True, encoding: str = "utf-8", ignore_errors: bool = False) -> Email:
        email = self._parse_email()
        if email.errors and not ignore_errors:
            raise ValueError("\n".join(email.errors))
        if html and "__mail.html" in self._files:
            assert self.id is not None
            email.html = self._adapter.get_file(self.id, "__mail.html").decode(encoding)
        return email

    def _parse_email(self) -> Email:
        if not isinstance(self._payload, dict):
            raise ValueError(f"Expected 'dict' payload, was '{type(self._payload).__name__}'")

        key = "email" if "email" in self._payload else "failedEmail" if "failedEmail" in self._payload else None
        if key is None:
            raise ValueError("No email in work item")
        try:
            email = Email.from_dict(self._payload[key])
        except KeyError as err:
            raise ValueError(f"Missing key in 'email' field: {err}") from err
        except Exception as err:
            raise ValueError(f"Malformed 'email' field: {err}") from err
        if key == "failedEmail":
            email.errors = self._parse_email_errors(self._payload)
        return email

    @staticmethod
    def _parse_email_errors(payload: dict[str, Any]) -> list[str]:
        errors = payload.get("errors", [])
        if not isinstance(errors, list):
            LOGGER.warning("Expected 'errors' as 'list', was '%s'", type(errors))
            return []
        result = []
        for error in errors:
            message = error["message"]
            if files := error.get("files"):
                message += f" ({', '.join(file['name'] for file in files)})"
            result.append(message)
        return result

    def get_file(self, name: str, path: PathType | None = None) -> Path:
        if name not in self.files:
            raise FileNotFoundError(f"No file with name: {name}")
        target = Path(os.getenv("ROBOT_ROOT", "")) / name if path is None else Path(path)
        assert self.id is not None
        target.write_bytes(self._adapter.get_file(self.id, name))
        return target.absolute()

    def get_files(self, pattern: str, path: PathType | None = None) -> list[Path]:
        root = Path(os.getenv("ROBOT_ROOT", "")) if path is None else Path(path)
        root.mkdir(parents=True, exist_ok=True)
        return [self.get_file(name, root / name) for name in self.files if fnmatch.fnmatch(name, pattern)]

    def create_output(self, payload: JSONType = None) -> "Output":
        assert self.id is not None
        item = Output(self._adapter, parent_id=self.id)
        if payload is not None:
            item.payload = payload
        state = self._get_lifecycle()
        self._set_lifecycle(replace(state, outputs=(*state.outputs, item)))
        return item

    def done(self) -> None:
        if self.released:
            raise RuntimeError("Work item already released")
        assert self.id is not None
        release_input(self._adapter, self.id, State.DONE, None)
        self._set_lifecycle(replace(self._get_lifecycle(), state=State.DONE))

    def fail(
        self,
        exception_type: ExceptionType | str = ExceptionType.APPLICATION,
        code: str | None = None,
        message: str | None = None,
    ) -> None:
        if self.released:
            raise RuntimeError("Work item already released")
        type_ = exception_type if isinstance(exception_type, ExceptionType) else ExceptionType(exception_type.upper())
        exception = {"type": type_.value, "code": code, "message": message}
        assert self.id is not None
        release_input(self._adapter, self.id, State.FAILED, exception)
        self._set_lifecycle(
            replace(self._get_lifecycle(), state=State.FAILED, exception=exception)
        )

    def download_file(self, name: str, path: PathType | None = None) -> Path:
        warnings.warn(
            "download_file() will be removed in version 2.x, use get_file()",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.get_file(name, path)

    def download_files(self, pattern: str, path: PathType | None = None) -> list[Path]:
        warnings.warn(
            "download_files() will be removed in version 2.x, use get_files()",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.get_files(pattern, path)


class Output(WorkItem):
    def __init__(self, adapter: "RuntimeAdapter", item_id: str | None = None, payload: JSONType = None, parent_id: str | None = None):
        super().__init__(adapter, item_id=item_id, payload=payload, parent_id=parent_id)

    def __enter__(self) -> "Output":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        if exc_type is None and not self.saved:
            self.save()
