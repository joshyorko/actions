import hashlib,json,os,subprocess,sys,zipfile
from pathlib import Path
root=Path(__file__).resolve().parent
os.environ.pop('ACTION_SERVER_SKIP_DOWNLOAD_IN_BUILD',None)
os.environ['PIP_CACHE_DIR']=str(root/'pip-cache')
wheelhouse=root/'wheelhouse';wheelhouse.mkdir()
archive=root/'actions_runtime-1.1.1.tar.gz'
subprocess.run([sys.executable,'-m','pip','wheel','--no-deps','--wheel-dir',str(wheelhouse),str(archive)],check=True)
wheel,=wheelhouse.glob('*.whl')
assert 'aarch64' in wheel.name
expected='e161f9d750776c376ef19ba15676b166447bc12096d208de2ecbbe51899cb1d2'
with zipfile.ZipFile(wheel) as z:
 rccs=[n for n in z.namelist() if '/bin/rcc-' in n]
 assert rccs==['actions/server/bin/rcc-18.19.12'],rccs
 assert hashlib.sha256(z.read(rccs[0])).hexdigest()==expected
record={'actions_source':'5fffa17e87bba4f1d0014e8ad48633102ac182f6','wheel':wheel.name,'wheel_sha256':hashlib.sha256(wheel.read_bytes()).hexdigest(),'source_archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'bundled_rcc_sha256':expected,'build_hook':'normal; no skip-download flag'}
(root/'wheel-record.json').write_text(json.dumps(record,indent=2)+'\n')
subprocess.run([sys.executable,'-m','pip','install','--only-binary=:all:',str(wheel)],check=True)
from actions.server._download_rcc import get_default_rcc_location
subprocess.run([sys.executable,str(root/'verify_linux_arm64_candidate.py'),'--official','--rcc',str(get_default_rcc_location()),'--rcc-sha256',expected,'--output',str(root/'receipt.json'),'--evidence-dir',str(root/'raw')],check=True)
