# Copyright 2022-2026 Robocorp and contributors.
# Licensed under the Apache License, Version 2.0.
import importlib
import json
from pathlib import Path

import pytest
from _pytest.outcomes import Failed, XFailed

from actions.work_items import Inputs, Outputs

from .mocks import MockAdapter

MANIFEST = json.loads(
    (Path(__file__).resolve().parents[3] / "contracts" / "ported-tests.json").read_text()
)
FAILURES = json.loads(
    (
        Path(__file__).resolve().parents[3]
        / "contracts"
        / "expected-red-failures.json"
    ).read_text()
)
CASES = {
    (case["origin"], case["source_test"]): case for case in MANIFEST["cases"]
}
FAILURES_BY_CASE = {failure["case_id"]: failure for failure in FAILURES["failures"]}
ORIGINS = {
    "test_custom_backends.py": ("custom-0.1.6", "test_adapters.py"),
    "test_robocorp_email.py": ("robocorp-1.5.0", "test_email.py"),
    "test_robocorp_file.py": ("robocorp-1.5.0", "test_adapters.py"),
    "test_robocorp_lifecycle.py": ("robocorp-1.5.0", "test_workitems.py"),
}
def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "contract_gap(exception, match/contains): exact call-phase expected-red ownership",
    )


def _resolve_exception(name):
    module_name, _, attribute = name.rpartition(".")
    if not module_name:
        raise ValueError(f"Contract gap exception must be fully qualified: {name}")
    return getattr(importlib.import_module(module_name), attribute)


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_call(item):
    outcome = yield
    marker = item.get_closest_marker("contract_gap")
    if marker is None:
        return

    expected = _resolve_exception(marker.kwargs["exception"])
    contains = marker.kwargs.get("contains")
    if contains is None:
        contains = (marker.kwargs["match"],)
    reason = marker.kwargs.get("reason", "owned contract gap")
    if outcome.excinfo is None:
        outcome.force_exception(
            Failed(
                f"[XPASS(strict)] {reason}; manifest update required",
                pytrace=False,
            )
        )
        return

    exception = outcome.excinfo[1]
    if type(exception) is expected and all(part in str(exception) for part in contains):
        outcome.force_exception(XFailed(reason, pytrace=False))


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
            failure = FAILURES_BY_CASE[case["id"]]
            parameter_id = item.callspec.id if hasattr(item, "callspec") else None
            if parameter_id not in failure["parameter_ids"]:
                raise AssertionError(
                    f"Undeclared expected-red parameter {case['id']}[{parameter_id}]"
                )
            item.add_marker(
                pytest.mark.contract_gap(
                    exception=failure["exception"],
                    contains=tuple(failure["predicate"]["contains"]),
                    reason=f'{case["implementation_task"]}: {case["id"]}',
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


@pytest.fixture
def context(adapter, inputs):
    class Context:
        def __init__(self):
            object.__setattr__(self, "_collection", inputs)

        def __setattr__(self, name, value):
            if name == "_inputs":
                self._collection._items = value
                self._collection._current = value[-1] if value else None
            else:
                object.__setattr__(self, name, value)

        @property
        def current_input(self):
            return self._collection.current

    context = Context()
    yield context
