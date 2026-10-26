import hashlib
import importlib.metadata
import json
from pathlib import Path
import sys
import zipfile

old_home = Path('/workspace/327-probes/a53-claimed/compiler/robocorp')
new_home = Path('/workspace/327-probes/a59-cold-rcc/acquire/robocorp')
assert not old_home.exists(), 'original cache path must be absent during proof'
assert Path(sys.prefix).resolve().is_relative_to(new_home)
wheel = Path('/workspace/327-artifacts/a53/wheels/actions_core-1.1.0a8-py3-none-any.whl')
assert hashlib.sha256(wheel.read_bytes()).hexdigest() == '42e550a8c207849e0a428fa702827ff2f77d98a00fd63aa0f85a912c0719419f'
dist = importlib.metadata.distribution('actions-core')
assert dist.version == '1.1.0a8'
members = 0
with zipfile.ZipFile(wheel) as z:
    for name in z.namelist():
        if name.endswith('/') or name.endswith('.dist-info/RECORD'):
            continue
        path = Path(dist.locate_file(name)).resolve()
        assert path.is_relative_to(new_home), name
        assert path.read_bytes() == z.read(name), name
        members += 1
import actions
import actions._action
assert Path(actions.__file__).resolve().is_relative_to(new_home)
assert Path(actions._action.__file__).resolve().is_relative_to(new_home)
print(json.dumps({'status':'PASS','prefix':sys.prefix,'core_version':dist.version,'wheel_members_verified_excluding_record':members,'old_cache_path_absent':True,'core_origin':actions.__file__},sort_keys=True))
