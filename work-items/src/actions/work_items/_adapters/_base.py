"""
Base adapter interface for work item storage.

Based on robocorp-workitems (Apache 2.0 License).
"""

from abc import ABC, abstractmethod
from typing import Any

from .._types import ExceptionType, JSONType, State


class BaseAdapter(ABC):
    """
    Abstract base class for work item storage adapters.

    Adapters implement the storage backend for work items, allowing
    different storage mechanisms (file-based, SQLite, cloud, etc.)
    to be used interchangeably.
    """

    @abstractmethod
    def reserve_input(self) -> str:
        """
        Reserve the next available input work item.

        Returns:
            Work item ID.

        Raises:
            EmptyQueue: If no work items are available.
        """
        pass

    @abstractmethod
    def release_input(
        self,
        item_id: str,
        state: State,
        exception_type: ExceptionType | None = None,
        code: str | None = None,
        message: str | None = None,
    ) -> None:
        """
        Release a reserved input work item.

        Args:
            item_id: Work item ID.
            state: Final state of the work item.
            exception_type: Type of exception if failed.
            code: Error code if failed.
            message: Error message if failed.
        """
        pass

    @abstractmethod
    def create_output(
        self,
        parent_id: str,
        payload: JSONType | None = None,
    ) -> str:
        """
        Create a new output work item.

        Args:
            parent_id: ID of the parent input work item.
            payload: Initial payload data.

        Returns:
            New work item ID.
        """
        pass

    @abstractmethod
    def load_payload(self, item_id: str) -> JSONType:
        """
        Load the payload of a work item.

        Args:
            item_id: Work item ID.

        Returns:
            Work item payload.
        """
        pass

    @abstractmethod
    def save_payload(self, item_id: str, payload: JSONType) -> None:
        """
        Save the payload of a work item.

        Args:
            item_id: Work item ID.
            payload: Payload data to save.
        """
        pass

    @abstractmethod
    def list_files(self, item_id: str) -> list[str]:
        """
        List files attached to a work item.

        Args:
            item_id: Work item ID.

        Returns:
            List of file names.
        """
        pass

    @abstractmethod
    def get_file(self, item_id: str, name: str) -> bytes:
        """
        Get file content from a work item.

        Args:
            item_id: Work item ID.
            name: File name.

        Returns:
            File content as bytes.
        """
        pass

    @abstractmethod
    def add_file(
        self,
        item_id: str,
        name: str,
        original_name: str,
        content: bytes,
    ) -> None:
        """
        Add a file to a work item.

        Args:
            item_id: Work item ID.
            name: File name in work item.
            original_name: Original file name.
            content: File content as bytes.
        """
        pass

    @abstractmethod
    def remove_file(self, item_id: str, name: str) -> None:
        """
        Remove a file from a work item.

        Args:
            item_id: Work item ID.
            name: File name.
        """
        pass

    # Extended methods for seeding and management

    def seed_input(
        self,
        payload: JSONType | None = None,
        files: dict[str, bytes] | None = None,
        queue_name: str | None = None,
    ) -> str:
        """
        Seed a new input work item into the queue.

        This is useful for testing or for producer tasks that create
        initial work items.

        Args:
            payload: Initial payload data.
            files: Files to attach as {name: content}.
            queue_name: Optional queue name override.

        Returns:
            New work item ID.
        """
        raise NotImplementedError("seed_input not implemented by this adapter")

    def list_items(
        self,
        queue_name: str | None = None,
        state: State | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """
        List work items in a queue.

        Args:
            queue_name: Queue name (None for default).
            state: Filter by state (None for all).
            limit: Maximum number of items to return.

        Returns:
            List of work item info dicts.
        """
        raise NotImplementedError("list_items not implemented by this adapter")

    def get_item(self, item_id: str) -> dict[str, Any]:
        """
        Get detailed info about a work item.

        Args:
            item_id: Work item ID.

        Returns:
            Work item info dict.
        """
        raise NotImplementedError("get_item not implemented by this adapter")

    def delete_item(self, item_id: str) -> None:
        """
        Delete a work item and its files.

        Args:
            item_id: Work item ID.
        """
        raise NotImplementedError("delete_item not implemented by this adapter")

    def get_queue_stats(self, queue_name: str | None = None) -> dict[str, int]:
        """
        Get statistics for a queue.

        Args:
            queue_name: Queue name (None for default).

        Returns:
            Dictionary with pending/in_progress/done/failed/total counts.
        """
        raise NotImplementedError("get_queue_stats not implemented by this adapter")
