"""Configuration helpers for this package's custom work item adapters."""

from __future__ import annotations

import logging
import os

LOGGER = logging.getLogger(__name__)


def _env_bool(name: str, default: bool) -> bool:
    """Parse an environment variable as a boolean.

    Missing values use ``default``. The values ``0``, ``false``, ``no``, and
    ``off`` are false, case-insensitively; all other values, including empty
    and whitespace-only strings, are true.
    """
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off"}


def get_adapter_config() -> dict[str, object]:
    """Load adapter configuration from environment variables."""
    config: dict[str, object] = {
        # Adapter selection (required)
        "adapter_class": os.getenv("RC_WORKITEM_ADAPTER", ""),
        # Common configuration
        "queue_name": os.getenv("RC_WORKITEM_QUEUE_NAME", "default"),
        "output_queue_name": os.getenv("RC_WORKITEM_OUTPUT_QUEUE_NAME", ""),
        "auto_append_output_suffix": _env_bool("RC_WORKITEM_AUTO_APPEND_OUTPUT_SUFFIX", True),
        "files_dir": os.getenv("RC_WORKITEM_FILES_DIR", "work_item_files"),
        "orphan_timeout_minutes": int(os.getenv("RC_WORKITEM_ORPHAN_TIMEOUT_MINUTES", "30")),
        # SQLite configuration
        "db_path": os.getenv("RC_WORKITEM_DB_PATH", ""),
        # Redis configuration
        "redis_url": os.getenv("RC_REDIS_URL", os.getenv("REDIS_URL", "")),
        "redis_host": os.getenv("REDIS_HOST", "localhost"),
        "redis_port": int(os.getenv("REDIS_PORT", "6379")),
        "redis_db": int(os.getenv("REDIS_DB", "0")),
        "redis_password": os.getenv("REDIS_PASSWORD"),
        # DocumentDB configuration
        "docdb_uri": os.getenv("DOCDB_URI", ""),
        "docdb_hostname": os.getenv("DOCDB_HOSTNAME", ""),
        "docdb_database": os.getenv("DOCDB_DATABASE", ""),
    }

    if not config["adapter_class"]:
        raise ValueError(
            "RC_WORKITEM_ADAPTER environment variable is required. "
            "Example: actions.work_items.SQLiteAdapter"
        )

    return config


def validate_adapter_config(adapter_class: str, config: dict[str, object]) -> None:
    """Validate required adapter-specific configuration."""
    adapter_class_path = adapter_class.lower()

    if (
        ("docdb" in adapter_class_path or "documentdb" in adapter_class_path)
        and not config.get("docdb_uri")
    ):
        if not config.get("docdb_hostname"):
            raise ValueError(
                "DOCDB_URI or DOCDB_HOSTNAME environment variable required for DocumentDB adapter."
            )
