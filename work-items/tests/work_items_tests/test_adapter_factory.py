"""Tests for adapter imports and factory selection."""

import sys
import types


def test_package_import_exports_optional_adapters():
    """Importing the package exposes optional adapters without optional deps installed."""
    import actions.work_items as work_items

    assert work_items.RedisAdapter.__name__ == "RedisAdapter"
    assert work_items.DocumentDBAdapter.__name__ == "DocumentDBAdapter"


def test_create_adapter_supports_redis_and_docdb_aliases(monkeypatch):
    """Common adapter aliases select the expected adapter classes."""
    import actions.work_items as work_items

    monkeypatch.setattr(work_items, "RedisAdapter", lambda **kwargs: ("redis", kwargs))
    monkeypatch.setattr(work_items, "DocumentDBAdapter", lambda **kwargs: ("docdb", kwargs))

    assert work_items.create_adapter("redis", queue_name="jobs") == (
        "redis",
        {"queue_name": "jobs"},
    )
    assert work_items.create_adapter("documentdb") == ("docdb", {})


def test_create_adapter_preserves_dynamic_class_name_case():
    """Dynamic adapter class paths keep class-name casing."""
    import actions.work_items as work_items

    module = types.ModuleType("test_dynamic_adapter_module")

    class CustomAdapter:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    module.CustomAdapter = CustomAdapter
    sys.modules[module.__name__] = module
    try:
        adapter = work_items.create_adapter(
            "test_dynamic_adapter_module.CustomAdapter",
            answer=42,
        )
    finally:
        sys.modules.pop(module.__name__, None)

    assert isinstance(adapter, CustomAdapter)
    assert adapter.kwargs == {"answer": 42}
