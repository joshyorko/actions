import ast,hashlib,json,os,stat,subprocess
from pathlib import Path
D=Path(__file__).parent;P=Path('/workspace/engineering/captured-child-cleanup-configured-full-proposal')
def binding(p):
 p=Path(p);z=p.read_bytes();return dict(path=str(p),bytes=len(z),sha256=hashlib.sha256(z).hexdigest())
def verify(r):assert binding(r['path'])==r,r['path']
old=P/'OWNERFINAL-cleanup499-managed-activation-configured-full-proposal.json';new=P/'OWNERFINAL-cleanup499-managed-activation-configured-full-proposal-v2.json'
a=json.loads(old.read_bytes());b=json.loads(new.read_bytes());assert binding(new)['sha256']=='e853c20af0045a217a4c979a973df807ae259c6a85e472fb20273a41dba882ac'
for row in b['bindings']:verify(row)
assert len(b['bindings'])==35
for k in a:
 if k not in {'schema','command','bindings'}:assert a[k]==b[k],k
assert a['schema'].replace('-v1','-v2')==b['schema']
ca=dict(a['command']);cb=dict(b['command']);aa=ca.pop('argv');ab=cb.pop('argv');assert ca==cb and aa[:-1]==ab[:-1]
original=(P/'planned_toolkit_configured_full_body.py').read_text();body=(P/'planned_toolkit_configured_full_body_v2.py').read_text()
assert original.count('repr(str(ROOT))')==1 and body==original.replace('repr(str(ROOT))','repr(str(root))')
assert ab[-1]==body
assert not any(isinstance(n,ast.Name) and n.id=='ROOT' for n in ast.walk(ast.parse(body)))
assert binding(old)==b['named_successor_disposition']['preserved_predecessor']
H=D/'OWNERFINAL-independent-cleanup499-managed-full-proposal-HOLD.json';h=json.loads(H.read_bytes())
for r in h['bindings']:verify(r)
l=json.loads(Path(b['LIGHT']['path']).read_bytes());o=json.loads(Path('/workspace/engineering/pr306-original-cleanup-deterministic-control-owned/OWNERFINAL-original-cleanup-deterministic-control-v2.json').read_bytes())
for r in l['bindings']+o['bindings']:verify(r)
root=Path(b['command']['cwd'])
def git(*args):return subprocess.check_output(['git','-C',str(root),*args])
assert git('rev-parse','HEAD').decode().strip()==b['head'] and git('rev-parse','HEAD^{tree}').decode().strip()==b['tree'] and git('status','--porcelain')==b''
proof=json.loads(Path('/workspace/engineering/captured-child-cleanup-independent-LIGHT-review/complete1422-independent-current-source-body-mode-proof-v2.json').read_bytes())
leaves={r.split(b'\t',1)[1].decode():r.split(b'\t',1)[0].split() for r in git('ls-tree','-r','-z','HEAD').split(b'\0') if r}
for r in proof['entries']:
 mode,kind,blob=leaves[r['path']];assert (mode.decode(),blob.decode())==(r['mode'],r['blob']);p=root/r['path'];s=p.lstat()
 if r['mode']=='120000':assert stat.S_ISLNK(s.st_mode);z=os.readlink(p).encode()
 else:assert stat.S_ISREG(s.st_mode) and bool(s.st_mode&stat.S_IXUSR)==(r['mode']=='100755');z=p.read_bytes()
 assert len(z)==r['bytes'] and hashlib.sha256(z).hexdigest()==r['sha256'];assert git('cat-file','blob',r['blob'])==z
assert len(leaves)==1422
assert not Path('/workspace/engineering/captured-child-cleanup-configured-full-once-owned').exists()
r={'schema':'independent-cleanup499-managed-full-named-successor-review-v2','decision':'GO_NAMED_V2_PROPOSAL_FOR_DISTINCT_ROOT_ONE_MANAGED_CONFIGURED_FULL_RELEASE_ONLY','head':b['head'],'tree':b['tree'],'proposal':binding(new),'corrected_body':binding(P/'planned_toolkit_configured_full_body_v2.py'),'original_HOLD':binding(H),'original_proposal':binding(old),'constructor':binding(__file__),'verification':{'only_runtime_delta':'Standalone undefined ROOT load corrected to defined root; exact other byte preservation','proposal_refs':35,'old_LIGHT_refs':67,'original_private_refs':31,'complete_source_Git_FS_blobs_modes':1422,'source_clean':True,'configured_task':'invoke test-not-integration unchanged via toolkit.poetry(action_server)','preflight_order':'same activated shell first; root300 rc0/source/30inputs/capacity then own5 origin checks before configured invoke','activation_exports_and_PATH':19,'primary_mode':'0700','fixture_mode':'0711','worker_count':2,'TERM_seconds':600,'KILL_grace_seconds':10,'attempts':1,'execution_namespace_absent_at_review':True,'executed_source_tests_preflight_body_RCC_or_gateway':False},'execution_prerequisites':b['execution_prerequisites'],'root_recording_requirements':['Rehash exact v2 proposal/body/all35 refs and current source before execution','Bind successful original current74 root300 terminal exact path/SHA and serialized heavy-slot environment','Fresh overlay>=1200000000 with no concurrent heavy/gateway/install/actual','One fresh root0700 namespace and0600 exclusive auth/log/terminal/post files; root actuallauncher needs its own exactbinding','Record actual returncode/time/private log hashes before postguard even on failure; no retry; incomplete receipts do not imply successful cleanup'],'scope_HOLD':['actual configured full result/SOURCEFINAL independent review','hosted causal Windows proof and unsampled failure cleanup','native274producer+5selected separately typed UNQUALIFIED','private/provider/browser/publication acceptance'],'Documentation_improvement':h['Documentation_improvement'],'Upstream_disposition':'none','bindings':b['bindings']}
r['Documentation_improvement']['Evidence']['corrected_body']=binding(P/'planned_toolkit_configured_full_body_v2.py');r['Documentation_improvement']['Remaining_uncertainty']='No execution performed; static one-name correction is accepted. Full result/current source acceptance/newnative/hosted cause remain unqualified.'
out=D/'OWNERFINAL-independent-cleanup499-managed-full-proposal-v2-review.json'
with out.open('x') as f:json.dump(r,f,indent=2);f.write('\n')
out.chmod(0o600);print(json.dumps(binding(out)))
