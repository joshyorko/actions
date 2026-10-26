import importlib.util
import os

# This has to be imported once and we're done.
# Note that this module may be imported multiple times (it's imported once
# and then it's removed from sys.modules and then reimported in a new run)
# as such, things that should be only done once need to be in a separate module.

try:
    import preload_actions_teardown  # type: ignore
except ImportError:
    from . import preload_actions_teardown  # noqa

# Selected child Core may predate the public HTML bridge. Ordinary execution
# does not need this optional annotation and must not load a fallback logger.
X_ACTION_TRACE = os.environ.get("X_ACTION_TRACE", "")

if X_ACTION_TRACE:
    import importlib.metadata
    import re
    from typing import Callable, Optional

    html: Optional[Callable[[str], None]] = None
    if importlib.util.find_spec("actions.server_integration") is not None:
        from actions import server_integration

        html = getattr(server_integration, "log_html", None)
    if html is None:
        # Explicit legacy distribution contract, not a catch-all import fallback.
        # Core a6/a7 removed this dependency and must not import upstream logging.
        requirements = importlib.metadata.requires("actions-core") or []
        legacy_logger = any(
            re.match(r"^robocorp[-_]log(?:[\s(<>=!~;\[]|$)", requirement, re.I)
            for requirement in requirements
        )
        if not legacy_logger:
            raise RuntimeError(
                "X_ACTION_TRACE requires the public log_html integration bridge; "
                "upgrade actions-core to 1.1.0a8 or newer. "
                "Ordinary execution without X_ACTION_TRACE remains supported."
            )
        from robocorp.log import html  # type: ignore[import-not-found,no-redef]

    assert html is not None
    html(
        f'<p style="line-height:34px">External <a href="{X_ACTION_TRACE}"'
        'style="color:rgb(var(--color-content-accent))">Client Application Trace</a> reported</p>'
    )
