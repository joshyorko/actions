import importlib.metadata
import json
import sys
from actions import action

@action
def durable_probe(value: int) -> str:
    """Return a deterministic synthetic result with worker provenance.

    Args:
        value: Synthetic integer to double.
    """
    import actions
    return json.dumps({"doubled": value * 2, "python": sys.version,
                       "core_version": importlib.metadata.version("actions-core"),
                       "core_origin": actions.__file__}, sort_keys=True)
