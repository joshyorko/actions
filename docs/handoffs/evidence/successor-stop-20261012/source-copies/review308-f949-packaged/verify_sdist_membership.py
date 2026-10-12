import hashlib
import json
from pathlib import Path
import subprocess
import tarfile

head='f949bef2eeab518ffd34d9e69955938a007f8922'
repo=Path('/workspace/actions-pr308')
root=Path('/workspace/successor-evidence/pr308-f949-packaged')
source=subprocess.check_output(['git','ls-tree','-r','--name-only',head,'--','action_server/src/actions/server'],cwd=repo,text=True).splitlines()
expected={p.removeprefix('action_server/src/'):p for p in source if p.endswith('.py')}
sdist=root/'actions_runtime-1.0.3.tar.gz'
prefix='actions_runtime-1.0.3/src/'
with tarfile.open(sdist) as archive:
    actual={m.name.removeprefix(prefix) for m in archive.getmembers() if m.isfile() and m.name.startswith(prefix+'actions/server/') and m.name.endswith('.py')}
    assert actual==set(expected)|{'actions/server/_oauth2_config.py'}
    for member,tracked in expected.items():
        data=archive.extractfile(prefix+member).read()
        assert data==subprocess.check_output(['git','show',head+':'+tracked],cwd=repo),member
receipt={'source_head':head,'source_tree':'ce5a94a37f108438daa9d2d283ab575b1000ce99','sdist_sha256':hashlib.sha256(sdist.read_bytes()).hexdigest(),'complete_python_member_set_equal':True,'tracked_python_members_exact':len(expected),'explicit_generated_member':'actions/server/_oauth2_config.py','build_executed':False,'scope':'static sdist source membership; no install/build/native qualification'}
(Path(__file__).parent/'sdist-complete-source-verification.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt))
