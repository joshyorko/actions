"""Linux isolated exact-source wheel build through the committed RCC toolkit."""
import argparse
import importlib.util
import json
from pathlib import Path
import shlex
import subprocess
import tempfile


def main():
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--inside-rcc',action='store_true');a=p.parse_args()
    root=a.source.resolve();out=a.output.resolve()
    tree=subprocess.check_output(['git','rev-parse','HEAD^{tree}'],cwd=root,text=True).strip()
    if tree!='f094faf5d2eabbef0a159a7fabb4983a59a8e56c':raise SystemExit('exact qualified a37 source tree required')
    if not a.inside_rcc:
        with tempfile.TemporaryDirectory(prefix='actions-a37-build-') as temp:
            robot=Path(temp)/'robot.json'
            command=shlex.join(['python',str(Path(__file__).resolve()),'--source',str(root),'--output',str(out),'--inside-rcc'])
            robot.write_text(json.dumps({'devTasks':{'Build':{'shell':command}},'environmentConfigs':[str(root/'developer/setup.yaml')]}))
            subprocess.run(['rcc','run','-r',str(robot),'--dev','-t','Build'],cwd=root,check=True)
        return
    spec=importlib.util.spec_from_file_location('actions_toolkit',root/'developer/toolkit.py');toolkit=importlib.util.module_from_spec(spec);spec.loader.exec_module(toolkit)
    toolkit.poetry('action_server','run','invoke','build-frontend')
    toolkit.poetry('action_server','run','invoke','build-oauth2-config')
    for package in ('actions','work-items','action_server'):
        toolkit.poetry(package,'build','--format','wheel','--output',str(out/package))
    import hashlib
    manifest={str(f.relative_to(out)):hashlib.sha256(f.read_bytes()).hexdigest() for f in out.rglob('*.whl')}
    (out/'rebuilt-sha256.json').write_text(json.dumps(manifest,indent=2)+'\n')


if __name__=='__main__':main()
