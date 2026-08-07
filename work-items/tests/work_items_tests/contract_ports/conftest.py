# Copyright 2022-2026 Robocorp and contributors.
# Licensed under the Apache License, Version 2.0.
import json
from pathlib import Path

import pytest
from _pytest.fixtures import FixtureLookupError
from _pytest.outcomes import Failed

from actions.work_items import Inputs, Outputs

from .mocks import MockAdapter

MANIFEST = json.loads(
    (Path(__file__).resolve().parents[3] / "contracts" / "ported-tests.json").read_text()
)
CASES = {
    (case["origin"], case["source_test"]): case for case in MANIFEST["cases"]
}
ORIGINS = {
    "test_custom_backends.py": ("custom-0.1.6", "test_adapters.py"),
    "test_robocorp_email.py": ("robocorp-1.5.0", "test_email.py"),
    "test_robocorp_file.py": ("robocorp-1.5.0", "test_adapters.py"),
    "test_robocorp_lifecycle.py": ("robocorp-1.5.0", "test_workitems.py"),
}
EXPECTED_EXCEPTIONS = {
    "custom-0.1.6.test_adapters.TestAdapterFactory.test_documentdb_adapter_requires_dependency": AssertionError,
    "custom-0.1.6.test_adapters.TestAdapterFactory.test_redis_adapter_requires_dependency": AssertionError,
    "custom-0.1.6.test_adapters.TestFileAdapter.test_empty_queue": FileExistsError,
    "custom-0.1.6.test_adapters.TestFileAdapter.test_malformed_queue": FileExistsError,
    "custom-0.1.6.test_adapters.TestFileAdapter.test_missing_file": Failed,
    "custom-0.1.6.test_adapters.TestSQLiteAdapter.test_database_initialization": AttributeError,
    "custom-0.1.6.test_adapters.TestSQLiteAdapter.test_reserve_and_release_workflow": AttributeError,
    "custom-0.1.6.test_adapters.TestSQLiteAdapter.test_file_operations": TypeError,
    "custom-0.1.6.test_adapters.TestSQLiteAdapter.test_failed_work_item_release": TypeError,
    "custom-0.1.6.test_adapters.TestSQLiteAdapter.test_producer_consumer_workflow": TypeError,
    "custom-0.1.6.test_adapters.TestSQLiteAdapter.test_work_item_with_files": TypeError,
    "custom-0.1.6.test_adapters.TestSQLiteAdapter.test_error_handling_file_already_exists": TypeError,
    "custom-0.1.6.test_adapters.TestSQLiteAdapter.test_custom_output_queue_name": AttributeError,
    "custom-0.1.6.test_adapters.TestSQLiteAdapter.test_default_output_queue_name_backward_compatibility": AttributeError,
    "robocorp-1.5.0.test_adapters.TestFileAdapter.test_empty_queue": FileExistsError,
    "robocorp-1.5.0.test_adapters.TestFileAdapter.test_malformed_queue": FileExistsError,
    "robocorp-1.5.0.test_adapters.TestFileAdapter.test_missing_file": Failed,
    "robocorp-1.5.0.test_workitems.module.test_collect_inputs": AssertionError,
    "robocorp-1.5.0.test_workitems.module.test_duplicate_reserve": Failed,
    "robocorp-1.5.0.test_workitems.module.test_input_fail": AssertionError,
    "robocorp-1.5.0.test_workitems.module.test_input_get_file_missing": KeyError,
    "robocorp-1.5.0.test_workitems.module.test_input_pass": AssertionError,
    "robocorp-1.5.0.test_workitems.module.test_input_remove_file_notexist": KeyError,
    "robocorp-1.5.0.test_workitems.module.test_inputs_iter": AssertionError,
    "robocorp-1.5.0.test_workitems.module.test_inputs_released": AssertionError,
    "robocorp-1.5.0.test_workitems.module.test_iter_after_release": AssertionError,
    "robocorp-1.5.0.test_workitems.module.test_outputs_create_no_current": FixtureLookupError,
    "robocorp-1.5.0.test_workitems.module.test_outputs_create_no_save": Failed,
}


def _expected_exception(case_id):
    if case_id in EXPECTED_EXCEPTIONS:
        return EXPECTED_EXCEPTIONS[case_id]
    if ".TestFileAdapter." in case_id:
        return FileExistsError
    if ".TestRedisAdapter." in case_id:
        return ImportError
    if ".TestDocumentDBAdapter." in case_id:
        return ModuleNotFoundError
    if ".test_email." in case_id:
        return AttributeError
    if ".test_workitems." in case_id:
        if any(token in case_id for token in ("context_raise", "raise_derived", "loop_raise", "throw_unknown", "release_work_item_failed")):
            return TypeError
        return AttributeError
    raise AssertionError(f"Missing expected failure type for {case_id}")


def pytest_collection_modifyitems(items):
    for item in items:
        port_name = Path(str(item.path)).name
        if port_name not in ORIGINS:
            continue
        origin, suite = ORIGINS[port_name]
        parts = [suite]
        if item.cls is not None:
            parts.append(item.cls.__name__)
        parts.append(item.originalname)
        case = CASES[(origin, "::".join(parts))]
        item._contract_case = case
        if case["status"] == "expected_red":
            item.add_marker(
                pytest.mark.xfail(
                    strict=True,
                    reason=f'{case["implementation_task"]}: {case["id"]}',
                    raises=_expected_exception(case["id"]),
                )
            )


@pytest.fixture
def adapter():
    adapter = MockAdapter()
    adapter.reset()
    yield adapter


@pytest.fixture
def inputs(adapter):
    collection = Inputs(adapter)
    collection.reserve()
    yield collection


@pytest.fixture
def outputs(adapter, inputs):
    yield Outputs(adapter, inputs)
