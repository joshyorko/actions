"""Clean committed-source candidate build, inside the pinned RCC toolkit."""
import hashlib,json,os,shutil,subprocess,sys,tarfile
from pathlib import Path
ROOT=Path('/workspace/actions'); BASE=Path('/workspace/recovery327/a42'); OUT=BASE/'evidence'
def run(args,**kw): return subprocess.run([str(x) for x in args],check=True,**kw)
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
if shutil.disk_usage(ROOT).free<8*1024**3: raise SystemExit('8 GiB disk preflight required')
BASE.mkdir(exist_ok=False);OUT.mkdir();SOURCE=BASE/'source';SOURCE.mkdir()
sha=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
if subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip(): raise SystemExit('clean source checkpoint required')
(BASE/'source-sha.txt').write_text(sha+'\n')
archive=BASE/'source.tar'
with archive.open('wb') as f: run(['git','archive',sha],cwd=ROOT,stdout=f)
with tarfile.open(archive) as t:t.extractall(SOURCE,filter='data')
archive.unlink()
metadata=BASE/'git-metadata.git'
run(['git','init','--bare',metadata]);run(['git','--git-dir='+str(metadata),'fetch',ROOT,sha]);run(['git','--git-dir='+str(metadata),'update-ref','--no-deref','HEAD',sha]);run(['git','--git-dir='+str(metadata),'read-tree',sha]);run(['git','--git-dir='+str(metadata),'config','core.bare','false']);run(['git','--git-dir='+str(metadata),'config','core.worktree',SOURCE]);(SOURCE/'.git').write_text('gitdir: '+str(metadata)+'\n')
rcc='action_server/src/actions/server/bin/rcc-18.19.3';(SOURCE/rcc).parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/rcc,SOURCE/rcc);(SOURCE/rcc).chmod(0o755)
# Prepared package tooling invokes only archived build tasks and public catalog.
run([ROOT/'action_server/.venv/bin/python','-m','invoke','build-frontend'],cwd=SOURCE/'action_server')
run([ROOT/'action_server/.venv/bin/python',SOURCE/'action_server/scripts/build_oauth2_config.py'],cwd=SOURCE/'action_server')
inputs={rel:digest(SOURCE/rel) for rel in (rcc,'action_server/src/actions/server/_static_contents.py','action_server/src/actions/server/_oauth2_config.py','action_server/frontend/package-lock.json')}
(OUT/'build-inputs.json').write_text(json.dumps({'source':sha,'inputs':inputs,'frontend':'npm ci from committed lock; both entrypoints rebuilt','oauth':'public archived catalog only'},indent=2)+'\n')
for package in ['action_server']:run(['poetry','build','--format','wheel','--output',BASE/'wheels'/package],cwd=SOURCE/package)
# Unchanged Core/Work Items source and exact frozen lock permit reuse of measured wheels.
assert not subprocess.check_output(['git','diff','f905c3888ecb448dbce80ce57a9b59ff041eb148',sha,'--','actions','work-items'],cwd=ROOT)
assert (SOURCE/'action_server/poetry.lock').read_bytes()==Path('/workspace/recovery327/a41/locked-consumer/runtime-poetry.lock').read_bytes()
for package in ('actions','work-items'):
    folder=BASE/'wheels'/package;folder.mkdir(parents=True)
    for wheel in (Path('/workspace/recovery327/a41/wheels')/package).glob('*.whl'):shutil.copyfile(wheel,folder/wheel.name)
constraints=Path('/workspace/recovery327/a41/locked-consumer/constraints.txt')
run([sys.executable,'-m','venv',BASE/'consumer']);python=BASE/'consumer/bin/python';wheels=list((BASE/'wheels').rglob('*.whl'))
run([python,'-m','pip','install','--no-cache-dir','-c',constraints,'--report',OUT/'install.json',*wheels]);run([python,'-m','pip','check'])
(OUT/'wheels.json').write_text(json.dumps({str(p.relative_to(BASE)):digest(p) for p in wheels},indent=2)+'\n')
run([python,'-I','-c',"import actions.server,importlib.metadata,pathlib; assert importlib.metadata.version('actions-runtime')=='1.1.0a42'; assert pathlib.Path(actions.server.__file__).is_relative_to('/workspace/recovery327/a42/consumer'); print('clean installed a42 import PASS')"],cwd=BASE)
