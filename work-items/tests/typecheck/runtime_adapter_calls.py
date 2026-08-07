from actions.work_items import RuntimeAdapter
from actions.work_items._types import ExceptionType, State


def valid_runtime_calls(adapter: RuntimeAdapter) -> None:
    adapter.release_input("item", State.DONE, None)
    adapter.release_input(
        "item", State.FAILED, exception={"type": "APPLICATION", "message": "failed"}
    )
    adapter.release_input(
        "item", State.FAILED, ExceptionType.APPLICATION, "E", "failed"
    )
    adapter.add_file("item", "stored.txt", b"data")
    adapter.add_file("item", "stored.txt", "source.csv", b"data")


def rejected_runtime_calls(adapter: RuntimeAdapter) -> None:
    adapter.release_input("item")  # type: ignore[call-overload]
    adapter.release_input("item", State.DONE, 42)  # type: ignore[call-overload]
    adapter.add_file("item", "stored.txt")  # type: ignore[call-overload]
    adapter.add_file("item", "stored.txt", 42)  # type: ignore[call-overload]
