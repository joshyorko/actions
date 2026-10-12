import importlib.util
from pathlib import Path
import toolkit
p=toolkit.REPOSITORY_ROOT/".github/workflows/_gen_workflows.py"
spec=importlib.util.spec_from_file_location("current_rcc_control_generator",p)
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
target=next(t for t in module.TARGETS if t.target=="actions_runtime_rcc_provider_rollback.yml")
target.generate()
print("Generated ONE RCC workflow")
