"""
Collection classes for work items - Inputs and Outputs.

Provides robocorp-workitems compatible API with singleton pattern
for easy access to work item queues.

Based on robocorp-workitems (Apache 2.0 License).
"""

import logging
from collections.abc import Iterator
from pathlib import Path
from typing import TYPE_CHECKING

from ._exceptions import EmptyQueue
from ._types import JSONType, PathType
from ._workitem import Input, Output

if TYPE_CHECKING:
    from ._adapters._base import BaseAdapter

log = logging.getLogger(__name__)


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

    def __init__(self, adapter: "BaseAdapter"):
        """
        Initialize inputs collection.

        Args:
            adapter: Storage adapter to use.
        """
        self._adapter = adapter
        self._current: Input | None = None
        self._items: list[Input] = []
        self._index = 0

    @property
    def current(self) -> Input | None:
        """
        The currently active input work item.

        Returns None if no item is currently being processed.
        """
        return self._current

    @property
    def released(self) -> list[Input]:
        """List of inputs that have been released (done or failed)."""
        return [item for item in self._items if item.released]

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
        return len(self._items)

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
        return self._items[index]

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
        self._current = item
        self._items.append(item)
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

    def __init__(self, adapter: "BaseAdapter", inputs: Inputs):
        """
        Initialize outputs collection.

        Args:
            adapter: Storage adapter to use.
            inputs: Associated Inputs collection.
        """
        self._adapter = adapter
        self._inputs = inputs
        self._items: list[Output] = []

    @property
    def last(self) -> Output | None:
        """
        The most recently created output work item.

        Returns None if no outputs have been created.
        """
        return self._items[-1] if self._items else None

    def __iter__(self) -> Iterator[Output]:
        """Iterate over created output work items."""
        return iter(self._items)

    def __len__(self) -> int:
        """Number of output work items created."""
        return len(self._items)

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
        return self._items[index]

    def __reversed__(self):
        return reversed(self._items)

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
            if isinstance(files, (str, Path)):
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

        self._items.append(output)
        return output
