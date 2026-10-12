import importlib.util
from pathlib import Path
path = Path("/workspace/engineering/runtime-checkout-eol/.github/workflows/_gen_workflows.py")
spec = importlib.util.spec_from_file_location("checkout_workflow_generator", path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
module.ActionServerTests().generate()
module.ActionServerPyPiRelease().generate()
