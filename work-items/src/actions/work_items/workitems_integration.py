"""Integration module for custom work item adapters.

This module provides utilities to dynamically load and use custom work item adapters
with existing tasks without modifying task code.

Environment Variables:
    RC_WORKITEM_ADAPTER: Full class path to adapter (e.g., "actions.work_items.SQLiteAdapter")
    RC_WORKITEM_DB_PATH: Database path for SQLite adapters
    RC_REDIS_URL: Redis connection URL for RedisAdapter
    DOCDB_URI: MongoDB/DocumentDB connection URI for DocumentDBAdapter

Usage:
    from actions.work_items.workitems_integration import get_adapter_instance

    # Get configured adapter
    adapter = get_adapter_instance()

    # Use adapter directly
    item_id = adapter.reserve_input()
    payload = adapter.load_payload(item_id)
"""

import logging
import os
from importlib import import_module

from ._adapters import BaseAdapter

# Import scripts.config lazily inside initialize_adapter to avoid import-time
# dependency on the scripts package for lightweight dev tasks (like seeding
# the SQLite DB) that don't need adapter configuration.

LOGGER = logging.getLogger(__name__)


# Global adapter instance (singleton per process)
_adapter_instance: BaseAdapter | None = None


def load_adapter_class(adapter_class_path: str) -> type[BaseAdapter]:
    """Dynamically import and return adapter class.

    Args:
        adapter_class_path: Full Python path to adapter class
                           (e.g., "actions.work_items.SQLiteAdapter")

    Returns:
        Adapter class (not instantiated)

    Raises:
        ImportError: If module or class cannot be imported
        AttributeError: If class doesn't exist in module
        ValueError: If class doesn't inherit from BaseAdapter

    Example:
        adapter_cls = load_adapter_class("actions.work_items.SQLiteAdapter")
        adapter = adapter_cls()  # Instantiate with __init__
    """
    try:
        # Split into module path and class name
        module_path, class_name = adapter_class_path.rsplit(".", 1)

        # Import module
        module = import_module(module_path)

        # Get class from module
        adapter_class = getattr(module, class_name)

        # Verify it's a BaseAdapter subclass
        if not issubclass(adapter_class, BaseAdapter):
            raise ValueError(f"Class {adapter_class_path} must inherit from BaseAdapter")

        LOGGER.info("Successfully loaded adapter class: %s", adapter_class_path)
        return adapter_class

    except (ImportError, AttributeError) as e:
        LOGGER.error("Failed to load adapter class %s: %s", adapter_class_path, e)
        raise ImportError(
            f"Cannot import adapter class '{adapter_class_path}'. "
            f"Ensure the module exists and class is defined. Error: {e}"
        ) from e


def initialize_adapter() -> BaseAdapter:
    """Initialize work item adapter from environment configuration.

    Reads RC_WORKITEM_ADAPTER environment variable to determine which adapter to use,
    validates configuration, and instantiates the adapter.

    Returns:
        Initialized adapter instance

    Raises:
        ValueError: If configuration is invalid or missing
        ImportError: If adapter class cannot be loaded

    Example:
        adapter = initialize_adapter()
        # Adapter is now ready to use
    """
    # Import adapter configuration utilities lazily so importing this module
    # doesn't fail when local config module is not present in minimal dev setups.
    try:
        from .scripts.config import get_adapter_config, validate_adapter_config
    except Exception as e:  # pragma: no cover - optional in some environments
        LOGGER.error("Missing adapter configuration utilities: %s", e)
        raise ImportError(
            "Required module 'actions.work_items.scripts.config' not found. "
            "Ensure actions.work_items.scripts.config is available."
        ) from e

    # Get adapter configuration
    config = get_adapter_config()
    adapter_class_path = str(config["adapter_class"])

    # Validate adapter-specific configuration
    validate_adapter_config(adapter_class_path, config)

    # Load adapter class
    adapter_class = load_adapter_class(adapter_class_path)

    # Instantiate adapter (configuration loaded from environment in __init__)
    try:
        adapter = adapter_class()
        LOGGER.info(
            "Adapter initialized successfully: %s (queue: %s)",
            adapter_class_path,
            config.get("queue_name", "default"),
        )
        return adapter
    except Exception as e:
        LOGGER.error("Failed to initialize adapter %s: %s", adapter_class_path, e)
        raise ValueError(
            f"Failed to initialize adapter '{adapter_class_path}'. "
            f"Check environment variables and adapter configuration. Error: {e}"
        ) from e


def get_adapter_instance(reinitialize: bool = False) -> BaseAdapter | None:
    """Get or create singleton adapter instance.

    This function returns a cached adapter instance. If no adapter is configured
    (RC_WORKITEM_ADAPTER not set), returns None, allowing tasks to fall back to
    the default actions.work_items behavior.

    Args:
        reinitialize: If True, force re-initialization of adapter

    Returns:
        Adapter instance, or None if no custom adapter configured

    Example:
        # In tasks.py
        adapter = get_adapter_instance()
        if adapter:
            # Use custom adapter
            item_id = adapter.reserve_input()
        else:
            # Fall back to actions.work_items default
            with workitems.inputs.current as item:
                ...
    """
    global _adapter_instance

    # Check if custom adapter is configured
    adapter_class_path = os.getenv("RC_WORKITEM_ADAPTER", "").strip()
    if not adapter_class_path:
        LOGGER.info("No custom adapter configured (RC_WORKITEM_ADAPTER not set)")
        return None

    # Return cached instance unless reinitialize requested
    if _adapter_instance is not None and not reinitialize:
        return _adapter_instance

    # Initialize new adapter
    try:
        _adapter_instance = initialize_adapter()
        return _adapter_instance
    except Exception as e:
        LOGGER.error("Failed to get adapter instance: %s", e)
        raise


def is_custom_adapter_enabled() -> bool:
    """Check if custom work item adapter is enabled.

    Returns:
        True if RC_WORKITEM_ADAPTER environment variable is set, False otherwise
    """
    return bool(os.getenv("RC_WORKITEM_ADAPTER", "").strip())


# Convenience exports
__all__ = [
    "get_adapter_instance",
    "initialize_adapter",
    "load_adapter_class",
    "is_custom_adapter_enabled",
]
