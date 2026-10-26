import subprocess,sys,os,hashlib,json,shutil,tarfile
from pathlib import Path
root=Path('/workspace/actions');base=Path('/workspace/actions-recovery-327/installed-a35'); evidence=base.parent/'evidence'
base.mkdir(exist_ok=False);source=base/'source';source.mkdir()
def run(args,**kw):return subprocess.run([str(a) for a in args],check=True,**kw)
sha=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip();(base/'source-sha.txt').write_text(sha+'\n')
archive=base/'source.tar'
with archive.open('wb') as stream:run(['git','archive',sha],cwd=root,stdout=stream)
with tarfile.open(archive) as stream:stream.extractall(source,filter='data')
archive.unlink()
metadata=base/'git-metadata.git';run(['git','init','--bare',metadata]);run(['git','--git-dir='+str(metadata),'fetch',root,sha]);run(['git','--git-dir='+str(metadata),'update-ref','--no-deref','HEAD',sha]);run(['git','--git-dir='+str(metadata),'read-tree',sha]);run(['git','--git-dir='+str(metadata),'config','core.bare','false']);run(['git','--git-dir='+str(metadata),'config','core.worktree',source]);(source/'.git').write_text('gitdir: '+str(metadata)+'\n')
inputs={}
for rel in ('action_server/src/actions/server/_static_contents.py','action_server/src/actions/server/bin/rcc-18.19.3'):
 target=source/rel;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(root/rel,target);inputs[rel]=hashlib.sha256(target.read_bytes()).hexdigest()
(source/'action_server/src/actions/server/bin/rcc-18.19.3').chmod(0o755)
# Only public archive inputs; protected root OAuth is never accessed.
run([root/'action_server/.venv/bin/python',source/'action_server/scripts/build_oauth2_config.py'],cwd=source/'action_server')
(base/'build-inputs.json').write_text(json.dumps({'source':sha,'copied':inputs,'oauth':'public archived catalog only'},indent=2)+'\n')
run(['poetry','build','--format','wheel','--output',base/'runtime-wheels'],cwd=source/'action_server')
run(['poetry','build','--format','wheel','--output',base/'core-wheels'],cwd=source/'actions')
shutil.copytree(base.parent/'installed-a27/sdk-wheels',base/'sdk-wheels')
shutil.copyfile(base.parent/'installed-a27/dependency-constraints.txt',base/'dependency-constraints.txt')
run([sys.executable,'-m','venv',base/'consumer'])
python=base/'consumer/bin/python';wheels=[next((base/d).glob('*.whl')) for d in ('runtime-wheels','core-wheels','sdk-wheels')]
run([python,'-m','pip','install','-c',base/'dependency-constraints.txt','--report',evidence/'a35-consumer-install.json',*wheels])
run([python,'-m','pip','check'])
verifier=base.parent/'verify-consumer-a35.py';verifier.write_text((base.parent/'verify-consumer-a27.py').read_text().replace('a27','a35'));run([python,'-I',verifier],cwd=base)
