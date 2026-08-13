"""
actions-runtime-common-internal is a library for common utilities to be shared across sema4ai
projects.

It should have as few dependencies as possible.

Each module should be a single utility (thus, actions.server._common doesn't directly
contain anything).
"""

__version__ = "0.3.0"
version_info = [int(x) for x in __version__.split(".")]
