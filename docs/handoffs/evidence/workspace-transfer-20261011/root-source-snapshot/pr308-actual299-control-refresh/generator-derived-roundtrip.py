from pathlib import Path
import hashlib, json, runpy, subprocess
import toolkit, yaml
root = toolkit.REPOSITORY_ROOT
out = Path('/workspace/engineering/pr308-actual299-control-refresh')
paths = [p for p in subprocess.check_output(['git', 'ls-files', '.github/*.yaml', '.github/*.yml'], cwd=root).decode().splitlines()]
assert len(paths) == 30
before = {p: (root / p).read_bytes() for p in paths}
namespace = runpy.run_path(str(root / '.github/workflows/_gen_workflows.py'), run_name='__main__')
for path, data in before.items():
    assert (root / path).read_bytes() == data, path
    yaml.load(data, Loader=yaml.BaseLoader)
names = [t.target for t in namespace['TARGETS']]
assert len(names) == len(set(names)) == 8
assert all('.github/workflows/' + p in before for p in names)
receipt = {'head': subprocess.check_output(['git','rev-parse','HEAD'],cwd=root).decode().strip(), 'generator':'.github/workflows/_gen_workflows.py', 'generated_outputs':names, 'generated_output_count':8, 'all_tracked_GitHub_YAML_count':len(paths), 'all30_GitHub_paths_parsed_and_bytes_preserved': {p:hashlib.sha256(b).hexdigest() for p,b in before.items()}, 'dependabot':'Preserved and parsed separately, not claimed as ninth generated workflow', 'no_changes_during_roundtrip':True}
(out/'generator-roundtrip-successor-v2-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print('8 generated workflows plus all30 tracked GitHub YAML/dependabot exact bytes and parse PASS')
