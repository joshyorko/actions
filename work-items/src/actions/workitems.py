"""Compatibility alias for importing work items as ``actions.workitems``."""

from . import work_items as _work_items
from .work_items import *  # noqa: F403

__all__ = list(_work_items.__all__)
