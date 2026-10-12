import pytest

from actions.server._robo_utils.callback import Callback


def test_callback_error_observer_preserves_later_consumers_and_order():
    seen = []
    failure = OSError("private callback failure")
    callback = Callback(on_error=lambda error: seen.append(("error", error)))

    def fail(value):
        seen.append(("failed", value))
        raise failure

    callback.register(fail)
    callback.register(lambda value: seen.append(("next", value)))
    callback(b"output")
    assert seen == [("failed", b"output"), ("error", failure), ("next", b"output")]
    assert callback.raise_exceptions is False


@pytest.mark.parametrize("raise_exceptions", [False, True])
def test_error_observer_failure_preserves_original_callback_contract(raise_exceptions):
    failure = ValueError("original private callback failure")
    calls = []

    def observe(error):
        calls.append(error)
        raise OSError("private observer failure")

    def fail(value):
        raise failure

    callback = Callback(raise_exceptions=raise_exceptions, on_error=observe)
    callback.register(fail)
    callback.register(lambda value: calls.append(value))
    if raise_exceptions:
        with pytest.raises(ValueError) as caught:
            callback(b"next")
        assert caught.value is failure
        assert calls == [failure]
    else:
        callback(b"next")
        assert calls == [failure, b"next"]
