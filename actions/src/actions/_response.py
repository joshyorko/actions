from typing import Annotated, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class Response(BaseModel, Generic[T]):
    """
    The response class provides a way for the user to signal that the action
    completed successfully with a given result or the action completed with
    some error (which the LLM can later show).
    """

    result: Annotated[
        T | None,
        Field(description="The result for the action if it ran successfully"),
    ] = None

    error: Annotated[
        str | None,
        Field(description="The error message if the action failed for some reason"),
    ] = None


class ActionError(RuntimeError):
    """
    This is a custom error which actions returning a `Response` are expected
    to raise if an "expected" exception happens.

    When this exception is raised actions-core will automatically convert
    it to an "expected" where its error message is the exception.

    i.e.: actions-core does something as:

    ```python
    try
        ...
    except ActionError as e:
        return Response(error=e.message)
    ```
    """
