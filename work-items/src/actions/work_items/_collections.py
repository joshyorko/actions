"""
Collection classes for work items - Inputs and Outputs.

Provides robocorp-workitems compatible API with singleton pattern
for easy access to work item queues.

Based on robocorp-workitems (Apache 2.0 License).
"""

import asyncio
import logging
import threading
from collections.abc import Iterator
from contextvars import ContextVar
from dataclasses import dataclass, replace
from pathlib import Path
from typing import TYPE_CHECKING

from ._exceptions import EmptyQueue
from ._types import JSONType, PathType
from ._workitem import Input, Output

if TYPE_CHECKING:
    from ._adapters._base import RuntimeAdapter

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class _InputsState:
    current: Input | None = None
    items: tuple[Input, ...] = ()


@dataclass(frozen=True)
class _OutputsState:
    items: tuple[Output, ...] = ()


def _owner() -> object:
    try:
        task = asyncio.current_task()
    except RuntimeError:
        task = None
    return task if task is not None else threading.current_thread()


class Inputs:
    """
    Collection of input work items.

    Provides iteration, indexing, and reservation of input work items
    from the queue. Compatible with robocorp-workitems API.

    Example:
        # Iterate over all inputs
        for item in inputs:
            process(item.payload)
            item.done()

        # Access current item
        current = inputs.current

        # Reserve explicitly
        item = inputs.reserve()
    """

    def __init__(self, adapter: "RuntimeAdapter"):
        """
        Initialize inputs collection.

        Args:
            adapter: Storage adapter to use.
        """
        self._adapter = adapter
        self._state: ContextVar[tuple[object, _InputsState] | None] = ContextVar(
            f"actions_work_items_inputs_state_{id(self)}", default=None
        )

    def _get_state(self) -> _InputsState:
        stored = self._state.get()
        owner = _owner()
        if stored is None or stored[0] is not owner:
            state = _InputsState()
            self._state.set((owner, state))
            return state
        return stored[1]

    def _set_state(self, state: _InputsState) -> None:
        self._state.set((_owner(), state))

    @property
    def _current(self) -> Input | None:
        return self._get_state().current

    @_current.setter
    def _current(self, value: Input | None) -> None:
        self._set_state(replace(self._get_state(), current=value))

    @property
    def _items(self) -> list[Input]:
        return list(self._get_state().items)

    @_items.setter
    def _items(self, value: list[Input]) -> None:
        self._set_state(replace(self._get_state(), items=tuple(value)))

    @property
    def current(self) -> Input | None:
        """
        The currently active input work item.

        Returns None if no item is currently being processed.
        """
        return self._get_state().current

    @property
    def released(self) -> list[Input]:
        """List of inputs that have been released (done or failed)."""
        return [item for item in self._get_state().items if item.released]

    @property
    def _all(self) -> tuple[Input, ...]:
        """Execution-local reservation history for context synchronization."""
        return self._get_state().items

    def __iter__(self) -> Iterator[Input]:
        """
        Iterate over available input work items.

        Each item is automatically reserved when yielded.
        Items must be released (done/fail) before the next
        item is retrieved.

        Yields:
            Input work items.
        """
        if self.current is not None and not self.current.released:
            with self.current as item:
                yield item
        while True:
            try:
                with self.reserve() as item:
                    yield item
            except EmptyQueue:
                break

    def __len__(self) -> int:
        """Number of items processed so far."""
        return len(self._get_state().items)

    def __getitem__(self, index: int) -> Input:
        """
        Get a previously processed item by index.

        Args:
            index: Zero-based index.

        Returns:
            Input work item.

        Raises:
            IndexError: If index out of range.
        """
        return self._get_state().items[index]

    def reserve(self) -> Input:
        """
        Reserve the next available input work item.

        Returns:
            Reserved Input work item.

        Raises:
            EmptyQueue: If no work items are available.
        """
        if self.current is not None and not self.current.released:
            raise RuntimeError("Previous input not released")
        item_id = self._adapter.reserve_input()
        item = Input(self._adapter, item_id)
        item.load()
        state = self._get_state()
        self._set_state(replace(state, current=item, items=(*state.items, item)))
        return item


class Outputs:
    """
    Collection of output work items.

    Provides creation and tracking of output work items.
    Compatible with robocorp-workitems API.

    Example:
        # Create output from current input
        outputs.create(payload={"result": "processed"})

        # Access last created output
        last = outputs.last

        # Create with files
        outputs.create(
            payload={"status": "done"},
            files={"report.pdf": "/path/to/report.pdf"}
        )
    """

    def __init__(self, adapter: "RuntimeAdapter", inputs: Inputs):
        """
        Initialize outputs collection.

        Args:
            adapter: Storage adapter to use.
            inputs: Associated Inputs collection.
        """
        self._adapter = adapter
        self._inputs = inputs
        self._state: ContextVar[tuple[object, _OutputsState] | None] = ContextVar(
            f"actions_work_items_outputs_state_{id(self)}", default=None
        )

    def _get_state(self) -> _OutputsState:
        stored = self._state.get()
        owner = _owner()
        if stored is None or stored[0] is not owner:
            state = _OutputsState()
            self._state.set((owner, state))
            return state
        return stored[1]

    def _set_state(self, state: _OutputsState) -> None:
        self._state.set((_owner(), state))

    @property
    def last(self) -> Output | None:
        """
        The most recently created output work item.

        Returns None if no outputs have been created.
        """
        items = self._get_state().items
        return items[-1] if items else None

    def __iter__(self) -> Iterator[Output]:
        """Iterate over created output work items."""
        return iter(self._get_state().items)

    def __len__(self) -> int:
        """Number of output work items created."""
        return len(self._get_state().items)

    def __getitem__(self, index: int) -> Output:
        """
        Get an output work item by index.

        Args:
            index: Zero-based index.

        Returns:
            Output work item.

        Raises:
            IndexError: If index out of range.
        """
        return self._get_state().items[index]

    def __reversed__(self):
        return reversed(self._get_state().items)

    def create(
        self,
        payload: JSONType | None = None,
        files: PathType | list[PathType] | dict[str, PathType | bytes] | None = None,
        save: bool = True,
    ) -> Output:
        """
        Create a new output work item.

        The output is linked to the current input work item.

        Args:
            payload: Initial payload data.
            files: Files to attach as {name: path_or_content}.
            save: Whether to immediately save (default True).

        Returns:
            Created Output work item.

        Raises:
            RuntimeError: If no current input exists.
        """
        current_input = self._inputs.current
        if current_input is None:
            raise RuntimeError(
                "No current input work item. "
                "Reserve an input before creating outputs."
            )

        output = current_input.create_output(payload)

        if files:
            if isinstance(files, str | Path):
                output.add_files(files)
            elif isinstance(files, dict):
                for name, value in files.items():
                    if isinstance(value, bytes):
                        output.add_file(content=value, name=name)
                    else:
                        output.add_file(path=value, name=name)
            else:
                for path in files:
                    output.add_file(path=path)

        if save:
            output.save()

        state = self._get_state()
        self._set_state(replace(state, items=(*state.items, output)))
        return output
