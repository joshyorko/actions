"""Read declared, eagerly prepared logical data in a trusted Action execution.

This API performs no query, network request, credential lookup or file access.
The trusted Runtime must explicitly install a verified execution context first.
"""
from ._context import scan

__all__ = ["scan"]
