from pathlib import Path
import hashlib, json, runpy, subprocess
import toolkit, yaml
root = toolkit.REPOSITORY_ROOT
out = Path('/workspace/engineering/pr300-actual299-refresh')
paths = subprocess.check_output(['git', 'ls-files', '*.yaml', '*.yml'], cwd=root).decode().splitlines()
assert len(paths) == 30
before = {p: (root / p).read_bytes() for p in paths}
runpy.run_path(str(root / '.github/workflows/_gen_workflows.py'), run_name='__main__')
for path, data in before.items():
    assert (root / path).read_bytes() == data, path
    yaml.load(data, Loader=yaml.BaseLoader)
names = ['actions_runtime_tests.yml', 'actions_runtime_pypi_release.yml', 'actions_runtime_rcc_provider_rollback.yml', 'actions_runtime_frozen_catalog_rollback.yml', 'actions_core_tests.yml', 'actions_core_pypi_release.yml', 'actions_work_items_tests.yml', 'actions_work_items_pypi_release.yml']
assert all('.github/workflows/' + p in before for p in names)
receipt = {'head': subprocess.check_output(['git','rev-parse','HEAD'],cwd=root).decode().strip(), 'generator':'.github/workflows/_gen_workflows.py', 'generated_outputs':names, 'generated_output_count':8, 'all_tracked_YAML_count':len(paths), 'all30_paths_parsed_and_bytes_preserved': {p:hashlib.sha256(b).hexdigest() for p,b in before.items()}, 'dependabot':'Preserved and parsed separately, not claimed as ninth generated workflow', 'no_pin_or_optin_changes':True}
(out/'generator-roundtrip-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print('8 generated workflows plus all30 tracked YAML/dependabot exact bytes and parse PASS')
