"""Import-friendly package alias for the ``actions-work-items`` distribution.

The published distribution name uses hyphens, which Python import statements
cannot parse. This package provides underscore-based imports:

    from actions_work_items import workitems
    import actions_work_items as workitems
"""

from actions import workitems as workitems
from actions.work_items import *  # noqa: F403
from actions.work_items import __all__ as _work_items_all
from actions.work_items import __version__

__all__ = [*_work_items_all, "workitems", "__version__"]
