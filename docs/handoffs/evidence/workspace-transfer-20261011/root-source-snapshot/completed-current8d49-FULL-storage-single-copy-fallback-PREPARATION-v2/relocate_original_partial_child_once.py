from pathlib import Path
import hashlib,json,os,stat,sys
HERE=Path('/workspace/engineering/completed-current8d49-FULL-storage-single-copy-fallback-PREPARATION-v2');OWNED=Path('/workspace/engineering/root-one-original-FULL-partial-relocation-owned-v1')
PLAN={'path': '/workspace/engineering/completed-current8d49-FULL-storage-single-copy-fallback-PREPARATION-v2/private-exact-original-partial-relocation-plan.json', 'bytes': 1408, 'sha256': 'e2ca10cd9b5604940edf35ed1d41003a2a146f439dddc1734c7babe5a4112742', 'mode': '0o444'};MODULE={'path': '/workspace/engineering/completed-current8d49-FULL-storage-single-copy-fallback-PREPARATION-v2/exact_failed_partial_relocation_v2.py', 'bytes': 6232, 'sha256': '9058cfc3e86ebbc7f8e765d8853a4883f27cebc068f4b08d25e7104c8be3a2bc', 'mode': '0o444'}
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def check(row):
 p=Path(row['path']);assert p.is_file() and not p.is_symlink() and p.stat().st_size==row['bytes'] and sha(p)==row['sha256'] and oct(stat.S_IMODE(p.stat().st_mode))==row['mode']
if __name__=='__main__':
 assert not sys.flags.optimize and sys.argv[1:]==['--one-consumed-root-partial-relocation',PLAN['sha256']]
 assert Path(sys.prefix).resolve()==Path('/workspace/actions-cloud/robocorp/holotree/c2fd1aa_5a1fac3_9fcd2534/bin/python').parent.parent.resolve()
 release=json.loads((OWNED/'consumed-exact-release.json').read_bytes())
 assert release['schema']=='ROOT_ONE_EXACT_FAILED_FULL_PARTIAL_RELOCATION_RELEASE_V1' and release['one_attempt'] is True and release['no_retry'] is True
 assert release['relocation_plan_binding']==PLAN and release['relocation_module_binding']==MODULE
 marker=OWNED/'original-relocation-child-started-once.json'
 with marker.open('xb') as f:os.fchmod(f.fileno(),0o600);f.write(b'{"one_attempt":true}\n');f.flush();os.fsync(f.fileno())
 check(PLAN);check(MODULE);raw=Path(MODULE['path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==MODULE['sha256']
 ns={'__name__':'verified_root_data_relocation'};exec(compile(raw,MODULE['path'],'exec'),ns)
 result=ns['relocate_once'](json.loads(Path(PLAN['path']).read_bytes()))
 print(json.dumps({'status':result['status'],'partial_gzip_complete':'UNKNOWN','native':'NOT_RUN'}))
