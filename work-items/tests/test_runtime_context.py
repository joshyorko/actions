import asyncio
from contextvars import Context, copy_context

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


def test_context_tracks_done_then_reserve_and_latest_output(caplog):
    adapter = MockAdapter()
    adapter.reset()
    context = work_items.init(adapter)
    first = work_items.inputs.current
    first.done()

    second = work_items.inputs.reserve()
    output = work_items.outputs.create(save=False)

    assert context.current_input is second
    assert output.parent_id == second.id
    assert context.outputs == [output]
    context.close()
    assert "unsaved changes that will be discarded" in caplog.text


def test_context_tracks_all_inputs_across_multiple_reservations():
    adapter = MockAdapter()
    adapter.reset()
    context = work_items.init(adapter)
    first = work_items.inputs.current
    first_output = work_items.outputs.create(save=False)
    first.done()
    second = work_items.inputs.reserve()
    second_output = work_items.outputs.create(save=False)

    assert context.current_input is second
    assert context.outputs == [first_output, second_output]


async def test_inherited_asyncio_tasks_do_not_share_collection_state():
    adapter = MockAdapter()
    adapter.reset()
    work_items.init(adapter)

    async def process_one():
        item = work_items.inputs.current
        output = work_items.outputs.create({"item": item.id}, save=False)
        await asyncio.sleep(0)
        item.done()
        return item, output, list(work_items.inputs.released), work_items.outputs.last

    first, second = await asyncio.gather(process_one(), process_one())

    assert first[0] is not second[0]
    assert first[1] is not second[1]
    assert first[2] == [first[0]]
    assert second[2] == [second[0]]
    assert first[3] is first[1]
    assert second[3] is second[1]


def test_copy_context_mutations_do_not_change_parent_collection_state():
    parent_adapter = MockAdapter()
    child_adapter = MockAdapter()
    parent_adapter.reset()
    child_adapter.reset()
    work_items.init(parent_adapter)
    parent_input = work_items.inputs.current

    child = copy_context()
    child_input, child_output = child.run(
        lambda: (
            work_items.init(child_adapter),
            work_items.inputs.current,
            work_items.outputs.create(save=False),
        )[1:]
    )

    assert child_input is not parent_input
    assert child_output is child.run(lambda: work_items.outputs.last)
    assert work_items.inputs.current is parent_input
    assert work_items.outputs.last is None


def test_copy_context_lifecycle_mutations_without_init_do_not_change_parent():
    adapter = MockAdapter()
    adapter.reset()
    context = work_items.init(adapter)
    parent_input = work_items.inputs.current
    parent_output = work_items.outputs.create(save=False)
    parent_input.done()

    child = copy_context()

    def mutate_child():
        child_input = work_items.inputs.reserve()
        child_output = work_items.outputs.create(save=False)
        child_input.fail(message="child")
        return child_input, child_output, list(work_items.inputs.released)

    child_input, child_output, child_released = child.run(mutate_child)

    assert child_input is not parent_input
    assert child_output.parent_id == child_input.id
    assert child_released == [parent_input, child_input]
    assert work_items.inputs.current is parent_input
    assert list(work_items.inputs.released) == [parent_input]
    assert work_items.outputs.last is parent_output
    assert context.current_input is parent_input
    assert context.outputs == [parent_output]
