from types import SimpleNamespace

import actions.work_items as work_items

from .work_items_tests.contract_ports.mocks import MockAdapter


class FakeTaskCache:
    def __init__(self):
        self.registered = []
        self.generator = None
        self.value = None

    def __call__(self, function):
        self.registered.append(function)

        def cached():
            if self.generator is None:
                self.generator = function()
                self.value = next(self.generator)
            return self.value

        cached.teardown = self.teardown
        return cached

    def teardown(self):
        try:
            next(self.generator)
        except StopIteration:
            pass


def test_optional_task_hook_registers_once_reuses_cache_and_closes_before_failure(
    monkeypatch, caplog
):
    adapter = MockAdapter()
    adapter.reset()
    cache = FakeTaskCache()
    task = SimpleNamespace(exc_info=(ValueError, ValueError("broken"), None))
    events = []

    original_close = work_items.WorkItemsContext.close
    original_release = adapter.release_input

    def close(context):
        events.append("close")
        original_close(context)

    def release(*args, **kwargs):
        events.append("release")
        return original_release(*args, **kwargs)

    monkeypatch.setattr(work_items.WorkItemsContext, "close", close)
    monkeypatch.setattr(adapter, "release_input", release)
    hook = work_items._build_task_context(cache, lambda: task, lambda: adapter)

    assert len(cache.registered) == 1
    first = hook()
    second = hook()
    first.get_input().create_output()
    cache.teardown()

    assert first is second
    assert events == ["close", "release"]
    assert adapter.releases[-1][0] == "workitem-id-first"
    assert "unsaved changes that will be discarded" in caplog.text


def test_optional_task_hook_fails_latest_unreleased_reserved_input(monkeypatch):
    adapter = MockAdapter()
    adapter.reset()
    cache = FakeTaskCache()
    task = SimpleNamespace(exc_info=(ValueError, ValueError("broken"), None))
    hook = work_items._build_task_context(cache, lambda: task, lambda: adapter)
    context = hook()
    work_items.set_context(context)
    work_items.inputs._reset()
    work_items.outputs._reset()
    first = work_items.inputs.current
    first.done()
    second = work_items.inputs.reserve()

    cache.teardown()

    assert adapter.releases[-1][0] == second.id
    assert second.released


def test_optional_task_hook_is_none_when_dependency_is_unavailable():
    assert work_items._build_task_context(None, None, lambda: None) is None
