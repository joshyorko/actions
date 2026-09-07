"""
A bare-bone AI Action template.

Please check out the base guidance on AI Actions in our main repository readme:
https://github.com/sema4ai/actions/blob/master/README.md
"""

from actions import action


@action
def greet() -> str:
    """Return a simple greeting."""
    return "Hello world!\n"
