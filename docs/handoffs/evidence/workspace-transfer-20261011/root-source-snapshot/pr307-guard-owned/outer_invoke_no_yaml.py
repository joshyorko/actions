"""Exercise the actual Invoke task with YAML forbidden in its outer interpreter."""
import importlib.abc
import sys

class NoOuterYaml(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == "yaml" or fullname.startswith("yaml."):
            raise ModuleNotFoundError("YAML intentionally unavailable in outer Invoke")

assert "yaml" not in sys.modules
sys.meta_path.insert(0, NoOuterYaml())
from invoke.program import Program

Program().run(argv=["invoke", "--search-root", sys.argv[1], "build-oauth2-config"])
assert "yaml" not in sys.modules
