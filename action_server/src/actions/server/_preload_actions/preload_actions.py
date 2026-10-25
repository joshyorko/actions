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

# This module runs inside the selected action package environment, which may
# retain an older Core. Only absence of the owned module selects its legacy
# logger; failures inside an available owned logger must propagate unchanged.
if importlib.util.find_spec("actions._logging") is None:
    from robocorp.log import html  # type: ignore[import-not-found]
else:
    from actions._logging import html

X_ACTION_TRACE = os.environ.get("X_ACTION_TRACE", "")

if X_ACTION_TRACE:
    html(
        f'<p style="line-height:34px">External <a href="{X_ACTION_TRACE}"'
        'style="color:rgb(var(--color-content-accent))">Client Application Trace</a> reported</p>'
    )
