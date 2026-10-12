import runpy
from pathlib import Path
p=Path("/workspace/engineering/pr312-actual309-refresh")
for n in ["verify-retained-native-helper-browser-post-light.py","verify-retained-V5-raw-and-driver-post-light.py","verify-committed-union-post-light.py"]:runpy.run_path(str(p/n),run_name="__main__")
