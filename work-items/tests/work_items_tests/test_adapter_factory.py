"""Tests for adapter imports and factory selection."""

import sys
import types


def test_package_import_exports_optional_adapters():
    """Importing the package exposes optional adapters without optional deps installed."""
    import actions.work_items as work_items

    assert work_items.RedisAdapter.__name__ == "RedisAdapter"
    assert work_items.DocumentDBAdapter.__name__ == "DocumentDBAdapter"


def test_actions_workitems_alias_exports_work_items_api():
    """The short actions.workitems alias exposes the same API surface."""
    from actions import workitems

    assert workitems.inputs is not None
    assert workitems.outputs is not None
    assert workitems.create_adapter is not None
    assert workitems.SQLiteAdapter.__name__ == "SQLiteAdapter"


def test_distribution_name_alias_exports_workitems_module():
    """The underscore package alias works for the hyphenated distribution name."""
    import actions_work_items
    from actions_work_items import workitems

    assert actions_work_items.inputs is workitems.inputs
    assert actions_work_items.outputs is workitems.outputs
    assert workitems.create_adapter is actions_work_items.create_adapter


def test_distribution_name_alias_exports_canonical_version():
    """The underscore package reports the canonical public version."""
    import actions.work_items as work_items
    import actions_work_items

    assert actions_work_items.__version__ == work_items.__version__ == "0.3.1"


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
