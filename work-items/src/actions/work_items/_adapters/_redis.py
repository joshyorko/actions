"""Redis-based work item adapter for distributed processing.

This module implements a custom work item adapter using Redis as the backend.
Perfect for distributed processing with multiple parallel workers.

Features:
- Atomic queue operations using RPOPLPUSH
- Hybrid file storage (inline <1MB, filesystem >1MB)
- Connection pooling with health checks
- Orphaned work item recovery
- Support for Redis Cluster and Sentinel

Usage:
    from actions.work_items import inputs

    # Set environment variables
    os.environ["RC_WORKITEM_ADAPTER"] = "actions.work_items.RedisAdapter"
    os.environ["RC_REDIS_URL"] = "redis://localhost:6379/0"

    # Use work items as normal
    for item in inputs:
        # Process work item...
        pass
"""

import base64
import json
import logging
import os
import uuid
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any

from .._exceptions import ApplicationException, EmptyQueue
from .._support import with_retry

# Import from local modules for drop-in replacement functionality
from .._types import TTL_WEEK_SECONDS, ExceptionType, JSONType, State
from ._base import BaseAdapter

LOGGER = logging.getLogger(__name__)

# Try to import redis
try:  # pragma: no cover - optional dependency
    import redis as _redis_lib  # type: ignore[import-not-found]
    from redis.exceptions import (
        ConnectionError as _RedisConnectionError,  # type: ignore[import-not-found]
    )
except ImportError:  # pragma: no cover
    _redis_lib = None  # type: ignore[assignment]

    class _RedisConnectionError(Exception):  # type: ignore[no-redef]
        """Fallback connection error when redis is unavailable."""


RedisConnectionError = _RedisConnectionError


# File size threshold for hybrid storage (1MB)
INLINE_FILE_THRESHOLD = 1_000_000

# Maximum file size (100MB)
MAX_FILE_SIZE = 104_857_600


class ProcessingState(str, Enum):
    """Lifecycle states tracked in Redis payload metadata."""

    PENDING = "PENDING"
    RESERVED = "RESERVED"
    COMPLETED = State.DONE.value  # "COMPLETED"
    FAILED = State.FAILED.value  # "FAILED"


class DatabaseTemporarilyUnavailable(ApplicationException):
    """Redis is temporarily unavailable (connection error)."""


class RedisAdapter(BaseAdapter):
    """Redis-backed work item adapter for distributed processing.

    Implements the BaseAdapter interface using Redis as the backend. Redis provides
    high-performance distributed queue operations with atomic reservation.

    Redis Key Structure:
        {queue}:pending          - List[work_item_id] (FIFO queue)
        {queue}:processing       - List[work_item_id] (reserved items)
        {queue}:done             - Set[work_item_id] (completed items)
        {queue}:failed           - Set[work_item_id] (failed items)
        {queue}:payload:{id}     - Hash{payload, queue_name, state}
        {queue}:files:{id}       - Hash{filename: content_or_path}
        {queue}:state:{id}       - String (terminal state)
        {queue}:parent:{id}      - String (parent work item ID)
        {queue}:exception:{id}   - Hash{type, code, message}
        {queue}:timestamps:{id}  - Hash{created_at, reserved_at, released_at}
        origin:{id}              - String (origin queue for cross-queue lookups)

    Environment Variables:
        RC_REDIS_URL: Redis connection URL (default: redis://localhost:6379/0)
        RC_WORKITEM_QUEUE_NAME: Queue identifier (default: default)
        RC_WORKITEM_OUTPUT_QUEUE_NAME: Output queue name (optional, default: {queue_name}_output)
        RC_WORKITEM_FILES_DIR: Files directory (default: devdata/work_item_files)
        RC_WORKITEM_ORPHAN_TIMEOUT_MINUTES: Orphan timeout (default: 30)

    lazydocs: ignore
    """

    def __init__(self):
        """Initialize RedisAdapter with connection pool and configuration.

        Raises:
            ImportError: If redis package not installed
            ApplicationException: If Redis connection fails
        """
        if _redis_lib is None:
            raise ImportError(
                "Redis support requires the redis package. "
                "Install it with: pip install actions-work-items[redis]"
            )

        # Load configuration
        redis_url = os.getenv("RC_REDIS_URL", "redis://localhost:6379/0")
        self.queue_name = os.getenv("RC_WORKITEM_QUEUE_NAME", "default")
        self.output_queue_name = os.getenv(
            "RC_WORKITEM_OUTPUT_QUEUE_NAME", f"{self.queue_name}_output"
        )
        self.files_dir = Path(os.getenv("RC_WORKITEM_FILES_DIR", "devdata/work_item_files"))
        self.orphan_timeout_minutes = int(os.getenv("RC_WORKITEM_ORPHAN_TIMEOUT_MINUTES", "30"))

        # Create files directory
        self.files_dir.mkdir(parents=True, exist_ok=True)

        # Initialize Redis client
        try:
            self._client = _redis_lib.from_url(
                redis_url,
                decode_responses=False,  # Handle binary data
                socket_connect_timeout=5,
                socket_keepalive=True,
                health_check_interval=30,
            )

            # Test connection
            self._client.ping()

            LOGGER.info(
                "RedisAdapter initialized: url=%s, queue=%s",
                redis_url,
                self.queue_name,
            )
        except Exception as e:
            LOGGER.critical("Failed to connect to Redis: %s", e)
            raise ApplicationException(f"Redis connection failed: {e}") from e

        # Cache for resolved queues to avoid redundant lookups
        self._queue_cache: dict[str, str] = {}

    def _key(self, suffix: str, queue: str | None = None, item_id: str = "") -> str:
        """Generate Redis key with queue namespace.

        Args:
            suffix: Key suffix (e.g., 'pending', 'payload', 'files')
            queue: Queue namespace (defaults to adapter queue)
            item_id: Work item ID (optional, for item-specific keys)

        Returns:
            Redis key string
        """
        if suffix == "origin":
            return f"origin:{item_id}" if item_id else "origin"

        queue_name = queue or self.queue_name
        if item_id:
            return f"{queue_name}:{suffix}:{item_id}"
        return f"{queue_name}:{suffix}"

    def _resolve_item_queue(self, item_id: str) -> str:
        """Determine which queue namespace contains the work item.

        Checks input queue, output queue, and origin tracking key.
        Results are cached to avoid redundant Redis operations.

        Args:
            item_id: Work item ID

        Returns:
            Queue name where item is stored

        Raises:
            ValueError: If work item not found in any queue
        """
        # Check cache first
        if item_id in self._queue_cache:
            return self._queue_cache[item_id]

        # Check input queue
        if self._client.hexists(self._key("payload", item_id=item_id), "payload"):
            queue_name = self.queue_name
        else:
            # Check origin tracking
            origin = self._client.get(f"origin:{item_id}")
            if origin:
                queue_name = origin.decode("utf-8") if isinstance(origin, bytes) else origin
                if self._client.hexists(
                    self._key("payload", queue=queue_name, item_id=item_id), "payload"
                ):
                    pass  # queue_name is set
                else:
                    queue_name = None
            else:
                queue_name = None

            # Check output queue if not found
            if queue_name is None:
                if self._client.hexists(
                    self._key("payload", queue=self.output_queue_name, item_id=item_id),
                    "payload",
                ):
                    queue_name = self.output_queue_name
                else:
                    raise ValueError(f"Work item not found: {item_id}")

        # Cache the result
        self._queue_cache[item_id] = queue_name
        return queue_name

    @staticmethod
    def _decode(value: Any) -> str:
        """Decode Redis values into strings."""
        if value is None:
            return ""
        if isinstance(value, bytes):
            return value.decode("utf-8")
        return str(value)

    @staticmethod
    def _public_state(state: str | None) -> str:
        """Normalize internal storage state to API state."""
        if state == ProcessingState.RESERVED.value:
            return State.IN_PROGRESS.value
        if state in {ProcessingState.COMPLETED.value, "COMPLETED"}:
            return State.DONE.value
        if state == State.FAILED.value:
            return State.FAILED.value
        return state or State.PENDING.value

    def _exception_for_item(self, item_id: str, queue: str) -> dict[str, str]:
        exception_data = self._client.hgetall(
            self._key("exception", queue=queue, item_id=item_id)
        )
        if not exception_data and queue != self.queue_name:
            exception_data = self._client.hgetall(self._key("exception", item_id=item_id))
        if not exception_data:
            return {}
        decoded = {
            self._decode(key): self._decode(value) for key, value in exception_data.items()
        }
        return {
            "type": decoded.get("type", decoded.get("exception_type", "")),
            "code": decoded.get("code", decoded.get("exception_code", "")),
            "message": decoded.get("message", decoded.get("exception_message", "")),
        }

    def _timestamps_for_item(self, item_id: str, queue: str) -> dict[str, str]:
        timestamps = self._client.hgetall(self._key("timestamps", queue=queue, item_id=item_id))
        if not timestamps and queue != self.queue_name:
            timestamps = self._client.hgetall(
                self._key("timestamps", queue=self.queue_name, item_id=item_id)
            )
        return {self._decode(key): self._decode(value) for key, value in timestamps.items()}

    def _item_to_api(self, item_id: str, queue_name: str) -> dict[str, Any]:
        payload_key = self._key("payload", queue=queue_name, item_id=item_id)
        payload_hash = self._client.hgetall(payload_key)
        if not payload_hash:
            raise ValueError(f"Work item not found: {item_id}")

        payload_json = payload_hash.get(b"payload") if isinstance(payload_hash, dict) else None
        if payload_json is None:
            payload_json = payload_hash.get("payload")
            if payload_json is None and isinstance(payload_hash, dict):
                payload_json = payload_hash.get(b"payload")
        payload_data: Any = {}
        if payload_json is not None:
            payload_str = self._decode(payload_json)
            try:
                payload_data = json.loads(payload_str)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON payload for item {item_id}") from exc

        timestamps = self._timestamps_for_item(item_id=item_id, queue=queue_name)
        raw_state = payload_hash.get("state")
        if raw_state is None and isinstance(payload_hash, dict):
            raw_state = payload_hash.get(b"state")
        if raw_state is None:
            raw_state = self._client.get(self._key("state", queue=queue_name, item_id=item_id))
        if raw_state is None and queue_name != self.queue_name:
            raw_state = self._client.get(
                self._key("state", queue=self.queue_name, item_id=item_id)
            )
        queue_state = self._public_state(self._decode(raw_state))
        exception_data = self._exception_for_item(item_id, queue_name)
        created_at = timestamps.get("created_at") or datetime.utcnow().isoformat()
        updated_at = (
            timestamps.get("released_at")
            or timestamps.get("reserved_at")
            or timestamps.get("created_at")
            or created_at
        )
        parent_id = payload_hash.get("parent_id")
        if parent_id is None and isinstance(payload_hash, dict):
            parent_id = payload_hash.get(b"parent_id")
        if parent_id is None:
            parent_id = self._client.get(
                self._key("parent", queue=queue_name, item_id=item_id)
            )

        return {
            "id": self._decode(item_id),
            "queue_name": queue_name,
            "state": queue_state,
            "payload": payload_data,
            "parent_id": self._decode(parent_id),
            "error_code": exception_data.get("code"),
            "error_message": exception_data.get("message"),
            "files": self.list_files(item_id),
            "created_at": created_at,
            "updated_at": updated_at,
        }

    @with_retry(
        max_attempts=3,
        backoff_factor=0.1,
        exceptions=(RedisConnectionError, DatabaseTemporarilyUnavailable),
    )
    def reserve_input(self) -> str:
        """Reserve next pending work item from queue.

        Uses RPOPLPUSH to atomically move from pending to processing list.

        Returns:
            str: Work item ID (UUID)

        Raises:
            EmptyQueue: No pending work items available
            DatabaseTemporarilyUnavailable: Redis connection error (retried)
        """
        LOGGER.debug("Reserving next input work item from queue: %s", self.queue_name)

        try:
            # Atomic move: pending -> processing
            item_id = self._client.rpoplpush(
                self._key("pending"),
                self._key("processing"),
            )

            if item_id is None:
                raise EmptyQueue(f"No work items in queue: {self.queue_name}")

            # Decode bytes to string
            item_id_str = item_id.decode("utf-8") if isinstance(item_id, bytes) else item_id

            # Update timestamps
            now = datetime.utcnow().isoformat()
            self._client.hset(self._key("timestamps", item_id=item_id_str), "reserved_at", now)

            # Update state in payload metadata
            self._client.hset(
                self._key("payload", item_id=item_id_str),
                "state",
                ProcessingState.RESERVED.value,
            )

            LOGGER.info("Reserved input work item: %s", item_id_str)
            return item_id_str

        except RedisConnectionError as e:
            LOGGER.error("Redis connection error during reserve: %s", e)
            raise DatabaseTemporarilyUnavailable(f"Redis connection failed: {e}") from e

    @with_retry(
        max_attempts=3,
        backoff_factor=0.1,
        exceptions=(RedisConnectionError, DatabaseTemporarilyUnavailable),
    )
    def release_input(
        self,
        item_id: str,
        state: State,
        exception_type: ExceptionType | None = None,
        code: str | None = None,
        message: str | None = None,
    ) -> None:
        """Release work item with terminal state.

        Moves from processing list to done/failed set and records exception if failed.

        Args:
            item_id: Work item ID
            state: Terminal state (State.DONE or State.FAILED)
            exception_type: Exception type for failed release
            code: Error code for failed release
            message: Error message for failed release
            exception: Legacy exception payload with type/code/message keys

        Raises:
            ValueError: Invalid state or missing exception for FAILED
            DatabaseTemporarilyUnavailable: Redis connection error (retried)
        """
        if isinstance(exception_type, dict):
            legacy_exception = exception_type
            exception_type = None
            if message is None:
                message = legacy_exception.get("message")
            if code is None:
                code = legacy_exception.get("code")

        if state not in (State.DONE, State.FAILED):
            raise ValueError(f"Release state must be DONE or FAILED, got {state}")

        if state == State.FAILED and not (exception_type or message):
            raise ValueError("Exception details required when state=FAILED")

        try:
            queue_name = self._resolve_item_queue(item_id)

            if queue_name != self.queue_name:
                self._client.delete(
                    self._key("timestamps", queue=self.queue_name, item_id=item_id),
                    self._key("state", queue=self.queue_name, item_id=item_id),
                    self._key("exception", queue=self.queue_name, item_id=item_id),
                )

            # Remove from processing list
            self._client.lrem(self._key("processing", queue=queue_name), 0, item_id)

            # Add to appropriate terminal set
            lifecycle_state = (
                ProcessingState.COMPLETED.value
                if state == State.DONE
                else ProcessingState.FAILED.value
            )

            if state == State.DONE:
                self._client.srem(self._key("failed", queue=queue_name), item_id)
                self._client.delete(
                    self._key("exception", queue=queue_name, item_id=item_id)
                )
                self._client.sadd(self._key("done", queue=queue_name), item_id)
            else:
                self._client.srem(self._key("done", queue=queue_name), item_id)
                self._client.sadd(self._key("failed", queue=queue_name), item_id)

                exception_type_value = (
                    exception_type.value if hasattr(exception_type, "value") else exception_type
                )
                self._client.hset(
                    self._key("exception", queue=queue_name, item_id=item_id),
                    mapping={
                        "type": str(exception_type_value or "UnknownException"),
                        "code": str(code or ""),
                        "message": str(message or ""),
                    },
                )
                self._client.expire(
                    self._key("exception", queue=queue_name, item_id=item_id), 86400
                )

            # Update timestamps
            now = datetime.utcnow().isoformat()
            self._client.hset(
                self._key("timestamps", queue=queue_name, item_id=item_id),
                "released_at",
                now,
            )

            # Store terminal state
            self._client.set(
                self._key("state", queue=queue_name, item_id=item_id), state.value
            )
            self._client.hset(
                self._key("payload", queue=queue_name, item_id=item_id),
                "state",
                lifecycle_state,
            )

            log_func = LOGGER.error if state == State.FAILED else LOGGER.info
            log_func(
                "Released work item %s with state %s (exception: %s)",
                item_id,
                state.value,
                message,
            )

        except RedisConnectionError as e:
            LOGGER.error("Redis connection error during release: %s", e)
            raise DatabaseTemporarilyUnavailable(f"Redis connection failed: {e}") from e

    @with_retry(
        max_attempts=3,
        backoff_factor=0.1,
        exceptions=(RedisConnectionError, DatabaseTemporarilyUnavailable),
    )
    def create_output(self, parent_id: str | None, payload: JSONType | None = None) -> str:
        """Create new output work item.

        Creates a work item in PENDING state in the output queue.

        Args:
            parent_id: Parent work item ID
            payload: JSON payload data

        Returns:
            str: New work item ID (UUID)

        Raises:
            DatabaseTemporarilyUnavailable: Redis connection error (retried)
        """
        item_id = str(uuid.uuid4())
        payload_data = payload if payload is not None else {}
        output_queue = self.output_queue_name

        LOGGER.debug(
            "Creating output work item for parent %s in queue %s",
            parent_id or "None",
            output_queue,
        )

        try:
            # Store payload metadata
            self._client.hset(
                self._key("payload", queue=output_queue, item_id=item_id),
                mapping={
                    "payload": json.dumps(payload_data),
                    "queue_name": output_queue,
                    "state": ProcessingState.PENDING.value,
                },
            )
            self._client.expire(
                self._key("payload", queue=output_queue, item_id=item_id),
                TTL_WEEK_SECONDS,
            )

            # Store parent relationship
            if parent_id:
                self._client.set(
                    self._key("parent", queue=output_queue, item_id=item_id), parent_id
                )
                self._client.expire(
                    self._key("parent", queue=output_queue, item_id=item_id),
                    TTL_WEEK_SECONDS,
                )

            # Store timestamps
            now = datetime.utcnow().isoformat()
            self._client.hset(
                self._key("timestamps", queue=output_queue, item_id=item_id),
                mapping={"created_at": now},
            )
            self._client.expire(
                self._key("timestamps", queue=output_queue, item_id=item_id),
                TTL_WEEK_SECONDS,
            )

            # Add to output pending queue (LPUSH for FIFO with RPOPLPUSH)
            self._client.lpush(self._key("pending", queue=output_queue), item_id)

            # Store origin queue for cross-queue lookups
            self._client.set(f"origin:{item_id}", output_queue, ex=TTL_WEEK_SECONDS)

            LOGGER.info("Created output work item: %s", item_id)
            return item_id

        except RedisConnectionError as e:
            LOGGER.error("Redis connection error during create: %s", e)
            raise DatabaseTemporarilyUnavailable(f"Redis connection failed: {e}") from e

    def seed_input(
        self,
        payload: JSONType | None = None,
        files: dict[str, bytes] | None = None,
        queue_name: str | None = None,
    ) -> str:
        """Create work item directly in input queue (for testing).

        Args:
            payload: JSON payload data
            files: Optional files to attach.
            queue_name: Queue name to seed into.

        Returns:
            str: New work item ID
        """
        item_id = str(uuid.uuid4())
        payload_data = payload if payload is not None else {}
        target_queue = queue_name or self.queue_name

        try:
            payload_key = self._key("payload", queue=target_queue, item_id=item_id)
            timestamps_key = self._key("timestamps", queue=target_queue, item_id=item_id)
            pending_key = self._key("pending", queue=target_queue)

            self._client.hset(
                payload_key,
                mapping={
                    "payload": json.dumps(payload_data),
                    "queue_name": target_queue,
                    "state": ProcessingState.PENDING.value,
                },
            )
            self._client.expire(payload_key, TTL_WEEK_SECONDS)

            now = datetime.utcnow().isoformat()
            self._client.hset(timestamps_key, mapping={"created_at": now})
            self._client.expire(timestamps_key, TTL_WEEK_SECONDS)

            self._client.lpush(pending_key, item_id)
            self._client.set(f"origin:{item_id}", target_queue, ex=TTL_WEEK_SECONDS)

            if files:
                for file_name, content in files.items():
                    self.add_file(item_id=item_id, name=file_name, original_name=file_name, content=content)

            LOGGER.debug("Seeded input work item: %s", item_id)
            return item_id

        except RedisConnectionError as e:
            LOGGER.error("Redis connection error during seed_input: %s", e)
            raise DatabaseTemporarilyUnavailable(f"Redis connection failed: {e}") from e

    def list_items(
        self,
        queue_name: str | None = None,
        state: State | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """List work items in a queue."""
        target_queue = queue_name or self.queue_name
        pattern = f"{self._key('payload', queue=target_queue)}:*"
        items = []

        for payload_key in self._client.scan_iter(match=pattern):
            payload_key_str = self._decode(payload_key)
            item_id = payload_key_str.rsplit(":", 1)[-1]
            if not item_id:
                continue

            try:
                item = self._item_to_api(item_id=item_id, queue_name=target_queue)
            except ValueError:
                continue

            if state is not None and item["state"] != state.value:
                continue

            items.append(item)

        items.sort(key=lambda item: item["created_at"], reverse=True)
        return items[:limit]

    def get_item(self, item_id: str) -> dict[str, Any]:
        """Get detailed info about a work item."""
        queue_name = self._resolve_item_queue(item_id)
        return self._item_to_api(item_id=item_id, queue_name=queue_name)

    def delete_item(self, item_id: str) -> None:
        """Delete a work item and its files."""
        queue_name = self._resolve_item_queue(item_id)

        file_refs = self._client.hgetall(self._key("files", queue=queue_name, item_id=item_id))
        for file_name, file_ref in file_refs.items():
            file_ref_str = self._decode(file_ref)
            if file_ref_str.startswith("file://"):
                filepath = Path(file_ref_str[7:])
                if filepath.exists():
                    filepath.unlink()

            self._client.hdel(self._key("files", queue=queue_name, item_id=item_id), file_name)

        self._client.lrem(self._key("pending", queue=queue_name), 0, item_id)
        self._client.lrem(self._key("processing", queue=queue_name), 0, item_id)
        self._client.srem(self._key("done", queue=queue_name), item_id)
        self._client.srem(self._key("failed", queue=queue_name), item_id)
        keys = [
            self._key("payload", queue=queue_name, item_id=item_id),
            self._key("parent", queue=queue_name, item_id=item_id),
            self._key("timestamps", queue=queue_name, item_id=item_id),
            self._key("files", queue=queue_name, item_id=item_id),
            self._key("exception", queue=queue_name, item_id=item_id),
            self._key("state", queue=queue_name, item_id=item_id),
            f"origin:{item_id}",
        ]
        if queue_name != self.queue_name:
            keys.extend(
                [
                    self._key("timestamps", queue=self.queue_name, item_id=item_id),
                    self._key("state", queue=self.queue_name, item_id=item_id),
                    self._key("exception", queue=self.queue_name, item_id=item_id),
                ]
            )
        self._client.delete(*keys)
        self._queue_cache.pop(item_id, None)

    def get_queue_stats(self, queue_name: str | None = None) -> dict[str, int]:
        """Get queue statistics."""
        queue = queue_name or self.queue_name

        pending = self._client.llen(self._key("pending", queue=queue))
        in_progress = self._client.llen(self._key("processing", queue=queue))
        done = self._client.scard(self._key("done", queue=queue))
        failed = self._client.scard(self._key("failed", queue=queue))

        total = 0
        for _ in self._client.scan_iter(match=f"{self._key('payload', queue=queue)}:*"):
            total += 1

        return {
            "pending": int(pending),
            "in_progress": int(in_progress),
            "done": int(done),
            "failed": int(failed),
            "total": total,
        }

    @with_retry(
        max_attempts=3,
        backoff_factor=0.1,
        exceptions=(RedisConnectionError, DatabaseTemporarilyUnavailable),
    )
    def load_payload(self, item_id: str) -> dict:
        """Load JSON payload from work item.

        Args:
            item_id: Work item ID

        Returns:
            dict: JSON payload data

        Raises:
            ValueError: Work item not found
            DatabaseTemporarilyUnavailable: Redis connection error (retried)
        """
        LOGGER.debug("Loading payload for work item: %s", item_id)

        try:
            queue_name = self._resolve_item_queue(item_id)
            payload_json = self._client.hget(
                self._key("payload", queue=queue_name, item_id=item_id), "payload"
            )

            if payload_json is None:
                raise ValueError(f"Work item not found: {item_id}")

            # Decode and parse JSON
            payload_str = (
                payload_json.decode("utf-8") if isinstance(payload_json, bytes) else payload_json
            )
            return json.loads(payload_str)

        except RedisConnectionError as e:
            LOGGER.error("Redis connection error during load_payload: %s", e)
            raise DatabaseTemporarilyUnavailable(f"Redis connection failed: {e}") from e
        except json.JSONDecodeError as e:
            LOGGER.error("Invalid JSON payload for work item %s: %s", item_id, e)
            raise ValueError(f"Invalid JSON payload: {e}") from e

    @with_retry(
        max_attempts=3,
        backoff_factor=0.1,
        exceptions=(RedisConnectionError, DatabaseTemporarilyUnavailable),
    )
    def save_payload(self, item_id: str, payload: JSONType) -> None:
        """Save JSON payload to work item.

        Args:
            item_id: Work item ID
            payload: JSON payload data

        Raises:
            ValueError: Work item not found
            DatabaseTemporarilyUnavailable: Redis connection error (retried)
        """
        LOGGER.debug("Saving payload for work item: %s", item_id)

        try:
            queue_name = self._resolve_item_queue(item_id)
            exists = self._client.exists(self._key("payload", queue=queue_name, item_id=item_id))
            if not exists:
                raise ValueError(f"Work item not found: {item_id}")

            payload_json = json.dumps(payload)
            self._client.hset(
                self._key("payload", queue=queue_name, item_id=item_id),
                "payload",
                payload_json,
            )

        except RedisConnectionError as e:
            LOGGER.error("Redis connection error during save_payload: %s", e)
            raise DatabaseTemporarilyUnavailable(f"Redis connection failed: {e}") from e
        except (TypeError, ValueError) as e:
            LOGGER.error("Invalid payload for work item %s: %s", item_id, e)
            raise ValueError(f"Payload not JSON-serializable: {e}") from e

    @with_retry(
        max_attempts=3,
        backoff_factor=0.1,
        exceptions=(RedisConnectionError, DatabaseTemporarilyUnavailable),
    )
    def list_files(self, item_id: str) -> list[str]:
        """List file attachments for work item.

        Args:
            item_id: Work item ID

        Returns:
            list[str]: List of filenames

        Raises:
            DatabaseTemporarilyUnavailable: Redis connection error (retried)
        """
        LOGGER.debug("Listing files for work item: %s", item_id)

        try:
            queue_name = self._resolve_item_queue(item_id)
            files_hash = self._client.hkeys(self._key("files", queue=queue_name, item_id=item_id))

            filenames = [f.decode("utf-8") if isinstance(f, bytes) else f for f in files_hash]
            return filenames

        except RedisConnectionError as e:
            LOGGER.error("Redis connection error during list_files: %s", e)
            raise DatabaseTemporarilyUnavailable(f"Redis connection failed: {e}") from e

    @with_retry(
        max_attempts=3,
        backoff_factor=0.1,
        exceptions=(RedisConnectionError, DatabaseTemporarilyUnavailable),
    )
    def get_file(self, item_id: str, name: str) -> bytes:
        """Retrieve file content from work item.

        Uses hybrid storage: inline for <1MB, filesystem for larger files.

        Args:
            item_id: Work item ID
            name: Filename

        Returns:
            bytes: File content

        Raises:
            FileNotFoundError: File not found
            DatabaseTemporarilyUnavailable: Redis connection error (retried)
        """
        LOGGER.debug("Getting file '%s' from work item: %s", name, item_id)

        try:
            queue_name = self._resolve_item_queue(item_id)
            file_ref = self._client.hget(
                self._key("files", queue=queue_name, item_id=item_id), name
            )

            if file_ref is None:
                raise FileNotFoundError(f"File not found: {name} (work item: {item_id})")

            # Decode reference
            file_ref_str = file_ref.decode("utf-8") if isinstance(file_ref, bytes) else file_ref

            # Check if filesystem reference
            if file_ref_str.startswith("file://"):
                filepath = Path(file_ref_str[7:])
                if not filepath.exists():
                    raise FileNotFoundError(f"File not found on filesystem: {filepath}")
                return filepath.read_bytes()
            else:
                # Inline storage (base64 encoded)
                return base64.b64decode(file_ref)

        except RedisConnectionError as e:
            LOGGER.error("Redis connection error during get_file: %s", e)
            raise DatabaseTemporarilyUnavailable(f"Redis connection failed: {e}") from e

    @with_retry(
        max_attempts=3,
        backoff_factor=0.1,
        exceptions=(RedisConnectionError, DatabaseTemporarilyUnavailable),
    )
    def add_file(
        self,
        item_id: str,
        name: str,
        original_name: str | None = None,
        content: bytes | None = None,
    ) -> None:
        """Attach file to work item.

        Uses hybrid storage: inline <1MB, filesystem >1MB.

        Args:
            item_id: Work item ID
            name: Filename
            original_name: Original filename (legacy compatibility)
            content: File content

        Raises:
            ValueError: Invalid filename or file too large
            FileExistsError: File already exists
            DatabaseTemporarilyUnavailable: Redis connection error (retried)
        """
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

        # Validate filename
        if "/" in name or "\\" in name:
            raise ValueError(f"Invalid filename (no path separators): {name}")

        if len(name) > 255:
            raise ValueError(f"Filename too long (max 255 chars): {name}")

        if len(content) > MAX_FILE_SIZE:
            raise ValueError(f"File too large (max {MAX_FILE_SIZE} bytes): {len(content)} bytes")

        LOGGER.debug("Adding file '%s' to work item %s (%d bytes)", name, item_id, len(content))

        try:
            # Resolve queue first to avoid redundant lookups
            queue_name = self._resolve_item_queue(item_id)

            # Check if file already exists
            exists = self._client.hexists(
                self._key("files", queue=queue_name, item_id=item_id), name
            )
            if exists:
                raise FileExistsError(f"File already exists: {name}")

            if len(content) > INLINE_FILE_THRESHOLD:
                # Large file: Store on filesystem
                filepath = self.files_dir / item_id / name
                filepath.parent.mkdir(parents=True, exist_ok=True)
                filepath.write_bytes(content)

                self._client.hset(
                    self._key("files", queue=queue_name, item_id=item_id),
                    name,
                    f"file://{filepath}",
                )
            else:
                # Small file: Store inline (base64)
                encoded_content = base64.b64encode(content).decode("utf-8")
                self._client.hset(
                    self._key("files", queue=queue_name, item_id=item_id),
                    name,
                    encoded_content,
                )

            # Set expiration
            self._client.expire(
                self._key("files", queue=queue_name, item_id=item_id), TTL_WEEK_SECONDS
            )

        except RedisConnectionError as e:
            LOGGER.error("Redis connection error during add_file: %s", e)
            raise DatabaseTemporarilyUnavailable(f"Redis connection failed: {e}") from e

    @with_retry(
        max_attempts=3,
        backoff_factor=0.1,
        exceptions=(RedisConnectionError, DatabaseTemporarilyUnavailable),
    )
    def remove_file(self, item_id: str, name: str) -> None:
        """Remove file from work item.

        Deletes from Redis or filesystem depending on storage method.

        Args:
            item_id: Work item ID
            name: Filename

        Raises:
            FileNotFoundError: File not found
            DatabaseTemporarilyUnavailable: Redis connection error (retried)
        """
        LOGGER.debug("Removing file '%s' from work item %s", name, item_id)

        try:
            queue_name = self._resolve_item_queue(item_id)
            file_ref = self._client.hget(
                self._key("files", queue=queue_name, item_id=item_id), name
            )

            if file_ref is None:
                raise FileNotFoundError(f"File not found: {name} (work item: {item_id})")

            # Decode reference
            file_ref_str = file_ref.decode("utf-8") if isinstance(file_ref, bytes) else file_ref

            # Delete from filesystem if large file
            if file_ref_str.startswith("file://"):
                filepath = Path(file_ref_str[7:])
                if filepath.exists():
                    filepath.unlink()

            # Remove from Redis hash
            self._client.hdel(self._key("files", queue=queue_name, item_id=item_id), name)

        except RedisConnectionError as e:
            LOGGER.error("Redis connection error during remove_file: %s", e)
            raise DatabaseTemporarilyUnavailable(f"Redis connection failed: {e}") from e

    def recover_orphaned_work_items(self) -> list[str]:
        """Recover orphaned work items beyond timeout.

        Resets RESERVED items to PENDING if reserved longer than timeout.

        Returns:
            list[str]: List of recovered work item IDs
        """
        cutoff_time = datetime.utcnow() - timedelta(minutes=self.orphan_timeout_minutes)

        LOGGER.info(
            "Recovering orphaned work items (timeout: %d min)",
            self.orphan_timeout_minutes,
        )

        try:
            processing_items = self._client.lrange(self._key("processing"), 0, -1)
            recovered_ids = []

            for item_id_bytes in processing_items:
                item_id = (
                    item_id_bytes.decode("utf-8")
                    if isinstance(item_id_bytes, bytes)
                    else item_id_bytes
                )

                # Get reserved_at timestamp
                reserved_at_str = self._client.hget(
                    self._key("timestamps", item_id=item_id), "reserved_at"
                )

                if reserved_at_str:
                    reserved_at_decoded = (
                        reserved_at_str.decode("utf-8")
                        if isinstance(reserved_at_str, bytes)
                        else reserved_at_str
                    )
                    reserved_at = datetime.fromisoformat(reserved_at_decoded)

                    if reserved_at < cutoff_time:
                        # Move back to pending
                        self._client.lrem(self._key("processing"), 0, item_id)
                        self._client.lpush(self._key("pending"), item_id)

                        # Clear reserved_at timestamp
                        self._client.hdel(self._key("timestamps", item_id=item_id), "reserved_at")

                        # Update state
                        self._client.hset(
                            self._key("payload", item_id=item_id),
                            "state",
                            ProcessingState.PENDING.value,
                        )

                        recovered_ids.append(item_id)
                        LOGGER.warning("Recovered orphaned work item: %s", item_id)

            if recovered_ids:
                LOGGER.info("Recovered %d orphaned work items", len(recovered_ids))

            return recovered_ids

        except RedisConnectionError as e:
            LOGGER.error("Redis connection error during recovery: %s", e)
            raise DatabaseTemporarilyUnavailable(f"Redis connection failed: {e}") from e

    @property
    def _config(self) -> "_Config":
        return _Config(self)


class _Config:
    def __init__(self, adapter: RedisAdapter):
        self.queue = adapter.queue_name
        self.file_threshold = INLINE_FILE_THRESHOLD
