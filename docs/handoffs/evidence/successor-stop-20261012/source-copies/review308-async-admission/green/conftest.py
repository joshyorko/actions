import importlib.util
import sys
from pathlib import Path
import actions.server as package

for leaf in ("_runs_state_cache", "_actions_run"):
    path = Path(__file__).parent / "action_server/src/actions/server" / (leaf + ".py")
    name = "actions.server." + leaf
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    setattr(package, leaf, module)
    spec.loader.exec_module(module)
