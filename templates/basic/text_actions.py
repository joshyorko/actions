"""An offline starter action using owned Core and Python's standard library."""

from actions import Response, action


@action
def count_words(text: str) -> Response[int]:
    """Count whitespace-separated words in the supplied text.

    Args:
        text: Text to count; empty or whitespace-only input returns zero.

    Returns:
        The number of whitespace-separated words.
    """
    return Response(result=len(text.split()))
