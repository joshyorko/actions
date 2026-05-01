"""Compatibility alias for ``actions.work_items``."""

from actions import workitems as _workitems
from actions.work_items import *  # noqa: F403

__all__ = list(_workitems.__all__)
