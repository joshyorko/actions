"""
Global context for work item management.

Based on robocorp-workitems (Apache 2.0 License).
"""

import asyncio
import logging
import os
import threading
from collections.abc import Iterator
from contextvars import ContextVar
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, cast

from ._exceptions import EmptyQueue
from ._types import JSONType
from ._workitem import Input, Output

if TYPE_CHECKING:
    from ._adapters._base import ManagedAdapter, RuntimeAdapter

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class _ContextState:
    current_input: Input | None = None
    inputs: tuple[Input, ...] = ()


class WorkItemsContext:
    """
    Context manager for work item input/output operations.

    This class manages the global state for work item processing,
    including the current input queue and adapter.
    """

    def __init__(self, adapter: "RuntimeAdapter"):
        """
        Initialize the context.

        Args:
            adapter: Storage adapter to use.
        """
        self._adapter = adapter
        self._state: ContextVar[tuple[object, _ContextState] | None] = ContextVar(
            f"actions_work_items_context_state_{id(self)}", default=None
        )

    @staticmethod
    def _owner() -> object:
        try:
            task = asyncio.current_task()
        except RuntimeError:
            task = None
        return task if task is not None else threading.current_thread()

    def _get_state(self) -> "_ContextState":
        stored = self._state.get()
        owner = self._owner()
        if stored is None or stored[0] is not owner:
            state = _ContextState()
            self._state.set((owner, state))
            return state
        return stored[1]

    def _set_state(self, state: "_ContextState") -> None:
        self._state.set((self._owner(), state))

    @property
    def _current_input(self) -> Input | None:
        return self._get_state().current_input

    @_current_input.setter
    def _current_input(self, value: Input | None) -> None:
        self._set_state(replace(self._get_state(), current_input=value))

    @property
    def _inputs(self) -> list[Input]:
        return list(self._get_state().inputs)

    @_inputs.setter
    def _inputs(self, value: list[Input]) -> None:
        self._set_state(replace(self._get_state(), inputs=tuple(value)))

    @property
    def adapter(self) -> "RuntimeAdapter":
        """The storage adapter."""
        return self._adapter

    @property
    def current_input(self) -> Input | None:
        """The currently reserved input work item."""
        state = self._get_state()
        if state.inputs:
            return state.inputs[-1]
        return state.current_input

    @property
    def outputs(self) -> list[Output]:
        state = self._get_state()
        items = state.inputs
        if not items and state.current_input is not None:
            items = (state.current_input,)
        return [output for item in items for output in item.outputs]

    def close(self) -> None:
        for output in self.outputs:
            if not output.saved:
                log.warning("%s has unsaved changes that will be discarded", output)

    def inputs(self) -> Iterator[Input]:
        """
        Iterate over available input work items.

        Yields:
            Input work items.

        Example:
            for item in ctx.inputs():
                # Process item
                item.done()
        """
        while True:
            try:
                item_id = self._adapter.reserve_input()
                input_item = Input(self._adapter, item_id)
                self._current_input = input_item
                yield input_item
            except EmptyQueue:
                break
            finally:
                self._current_input = None

    def get_input(self) -> Input:
        """
        Get the next input work item.

        Returns:
            Input work item.

        Raises:
            EmptyQueue: If no work items are available.
        """
        item_id = self._adapter.reserve_input()
        input_item = Input(self._adapter, item_id)
        self._current_input = input_item
        return input_item

    def create_output(
        self,
        payload: JSONType | None = None,
        files: dict | None = None,
        save: bool = False,
    ) -> Output:
        """
        Create a new output work item.

        Args:
            payload: Initial payload data.
            files: Files to attach as {name: path_or_content}.
            save: Whether to immediately save the output.

        Returns:
            Output work item.

        Raises:
            RuntimeError: If no current input is set.
        """
        if self._current_input is None:
            raise RuntimeError("No current input - cannot create output")

        output = self._current_input.create_output(payload)

        if files:
            for name, value in files.items():
                if isinstance(value, str | os.PathLike):
                    output.add_file(path=value, name=name)
                else:
                    output.add_file(content=value, name=name)

        if save:
            output.save()

        return output

    def seed_input(
        self,
        payload: JSONType | None = None,
        files: dict | None = None,
        queue_name: str | None = None,
    ) -> str:
        """
        Seed a new input work item.

        Args:
            payload: Initial payload data.
            files: Files to attach as {name: content}.
            queue_name: Optional queue name override.

        Returns:
            New work item ID.
        """
        files_bytes = None
        if files:
            files_bytes = {}
            for name, value in files.items():
                if isinstance(value, str | os.PathLike):
                    from pathlib import Path
                    files_bytes[name] = Path(value).read_bytes()
                else:
                    files_bytes[name] = value

        managed = cast("ManagedAdapter", self._adapter)
        return managed.seed_input(payload, files_bytes, queue_name)


# Global context instance
_context: ContextVar[WorkItemsContext | None] = ContextVar("actions_work_items_context", default=None)


def get_context() -> WorkItemsContext:
    """
    Get the global work items context.

    Returns:
        The global WorkItemsContext instance.

    Raises:
        RuntimeError: If context not initialized.
    """
    context = _context.get()
    if context is None:
        raise RuntimeError(
            "Work items context not initialized. "
            "Call work_items.init() first or set environment variables."
        )
    return context


def init(adapter: "RuntimeAdapter | None" = None) -> WorkItemsContext:
    """
    Initialize the global work items context.

    If no adapter is provided, one will be created based on
    environment variables.

    Args:
        adapter: Optional storage adapter.

    Returns:
        The initialized context.
    """
    if adapter is None:
        adapter = _create_adapter_from_env()

    context = WorkItemsContext(adapter)
    _context.set(context)
    return context


def set_context(context: WorkItemsContext) -> None:
    """Install an existing context in the current execution context."""
    _context.set(context)


def _create_adapter_from_env() -> "RuntimeAdapter":
    """
    Create an adapter based on environment variables.

    Environment variables:
        RC_WORKITEM_ADAPTER: Adapter class path (default: SQLiteAdapter)
        RC_WORKITEM_DB_PATH: SQLite database path (default: ./workitems.db)
        RC_WORKITEM_QUEUE_NAME: Input queue name (default: default)
        RC_WORKITEM_OUTPUT_QUEUE_NAME: Output queue name (default: {queue}_output)
        RC_WORKITEM_FILES_DIR: Files directory (default: ./work_item_files)

    Returns:
        Configured adapter instance.
    """
    adapter_class = os.environ.get(
        "RC_WORKITEM_ADAPTER",
        "actions.work_items.SQLiteAdapter"
    )

    # Import the adapter class
    if adapter_class == "actions.work_items.SQLiteAdapter":
        from ._adapters._sqlite import SQLiteAdapter
        db_path = os.environ.get("RC_WORKITEM_DB_PATH", "./workitems.db")
        queue_name = os.environ.get("RC_WORKITEM_QUEUE_NAME", "default")
        output_queue_name = os.environ.get(
            "RC_WORKITEM_OUTPUT_QUEUE_NAME",
            f"{queue_name}_output"
        )
        files_dir = os.environ.get("RC_WORKITEM_FILES_DIR", "./work_item_files")

        return SQLiteAdapter(
            db_path=db_path,
            queue_name=queue_name,
            output_queue_name=output_queue_name,
            files_dir=files_dir,
        )
    else:
        # Dynamic import for custom adapters
        import importlib
        module_path, class_name = adapter_class.rsplit(".", 1)
        module = importlib.import_module(module_path)
        adapter_cls = getattr(module, class_name)
        return adapter_cls()


# Convenience functions for common operations

def inputs() -> Iterator[Input]:
    """
    Iterate over input work items.

    This is a convenience function that uses the global context.

    Yields:
        Input work items.
    """
    return get_context().inputs()


def get_input() -> Input:
    """
    Get the next input work item.

    This is a convenience function that uses the global context.

    Returns:
        Input work item.
    """
    return get_context().get_input()


def create_output(
    payload: JSONType | None = None,
    files: dict | None = None,
    save: bool = False,
) -> Output:
    """
    Create an output work item.

    This is a convenience function that uses the global context.

    Args:
        payload: Initial payload data.
        files: Files to attach.
        save: Whether to immediately save.

    Returns:
        Output work item.
    """
    return get_context().create_output(payload, files, save)


def seed_input(
    payload: JSONType | None = None,
    files: dict | None = None,
    queue_name: str | None = None,
) -> str:
    """
    Seed a new input work item.

    This is a convenience function that uses the global context.

    Args:
        payload: Initial payload data.
        files: Files to attach.
        queue_name: Optional queue name override.

    Returns:
        New work item ID.
    """
    return get_context().seed_input(payload, files, queue_name)
