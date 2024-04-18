from dataclasses import asdict
from pathlib import Path
from typing import Callable, Optional, overload

from ._action_options import ActionOptions
from ._fixtures import setup, teardown
from ._protocols import IAction, Status
from ._request import Request
from ._secret import Secret

__version__ = "0.3.0"
version_info = [int(x) for x in __version__.split(".")]


@overload
def action(func: Callable) -> Callable:
    ...


@overload
def action(func: Callable, **kwargs: Optional[ActionOptions]) -> Callable:
    ...


def action(*args, **kwargs):
    """
    Decorator for actions (entry points) which can be executed by `sema4ai.actions`.

    i.e.:

    If a file such as actions.py has the contents below:

    ```python
    from sema4ai.actions import action

    @action
    def enter_user() -> str:
        ...
    ```

    It'll be executable by sema4ai actions as:

    python -m sema4ai.actions run actions.py -a enter_user

    Args:
        func: A function which is a action to `sema4ai.actions`.
        is_consequential: Whether the action is consequential or not. This will add `x-openai-isConsequential: true` to the action metadata and shown in OpenApi spec.
    """

    def decorator(*args, **kwargs):
        # i.e.: This is just a thin layer for the task decorator at this point
        # (it may be extended in the future...).
        from sema4ai.tasks import task

        options = ActionOptions(**kwargs)

        return task(*args, **asdict(options))

    if args and callable(args[0]):
        return decorator(args[0], **kwargs)

    return lambda func: decorator(func, **kwargs)


def session_cache(func):
    """
    Provides decorator which caches return and clears automatically when all
    actions have been run.

    A decorator which automatically cache the result of the given function and
    will return it on any new invocation until sema4ai-actions finishes running
    all actions.

    The function may be either a generator with a single yield (so, the first
    yielded value will be returned and when the cache is released the generator
    will be resumed) or a function returning some value.

    Args:
        func: wrapped function.
    """
    from sema4ai.tasks import session_cache

    return session_cache(func)


def action_cache(func):
    """
    Provides decorator which caches return and clears it automatically when the
    current action has been run.

    A decorator which automatically cache the result of the given function and
    will return it on any new invocation until sema4ai-actions finishes running
    the current action.

    The function may be either a generator with a single yield (so, the first
    yielded value will be returned and when the cache is released the generator
    will be resumed) or a function returning some value.

    Args:
        func: wrapped function.
    """
    from sema4ai.tasks import task_cache

    return task_cache(func)


def get_output_dir() -> Optional[Path]:
    """
    Provide the output directory being used for the run or None if there's no
    output dir configured.
    """
    from sema4ai.tasks import get_output_dir

    return get_output_dir()


def get_current_action() -> Optional[IAction]:
    """
    Provides the action which is being currently run or None if not currently
    running an action.
    """
    from sema4ai.tasks import get_current_action

    return get_current_action()


__all__ = [
    "IAction",
    "Request",
    "Secret",
    "Status",
    "action",
    "action_cache",
    "get_current_action",
    "get_output_dir",
    "session_cache",
    "setup",
    "teardown",
]
