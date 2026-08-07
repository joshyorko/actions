from contextvars import Context

import actions.work_items as work_items

from .work_items_tests.contract_ports.mocks import MockAdapter


def test_init_is_context_local():
    first_adapter = MockAdapter()
    second_adapter = MockAdapter()
    first_adapter.reset()
    second_adapter.reset()

    def initialize(adapter):
        work_items.init(adapter)
        return work_items.get_context(), work_items.inputs.current

    first_context, first_input = Context().run(initialize, first_adapter)
    second_context, second_input = Context().run(initialize, second_adapter)

    assert first_context.adapter is first_adapter
    assert second_context.adapter is second_adapter
    assert first_input is not second_input


def test_unsaved_outputs_warn_when_context_is_closed(caplog):
    adapter = MockAdapter()
    adapter.reset()
    context = work_items.init(adapter)
    work_items.inputs.current.create_output()

    context.close()

    assert "unsaved changes that will be discarded" in caplog.text
