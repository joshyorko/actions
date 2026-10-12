import ast,hashlib,json,os,stat,subprocess
from pathlib import Path
D=Path(__file__).parent
P=Path('/workspace/engineering/captured-child-cleanup-configured-full-proposal/OWNERFINAL-cleanup499-managed-activation-configured-full-proposal.json')
R=Path('/workspace/engineering/captured-child-cleanup')
def b(p):
 p=Path(p); z=p.read_bytes(); return dict(path=str(p),bytes=len(z),sha256=hashlib.sha256(z).hexdigest())
def v(row):
 assert b(row['path'])==row,row['path']
x=json.loads(P.read_bytes());assert b(P)['sha256']=='8324bc634159cc6c84c867fa54bd6f3681c5c085f95a5d0ab7ebcfa72269b72c'
for row in x['bindings']:v(row)
l=json.loads(Path(x['LIGHT']['path']).read_bytes())
for row in l['bindings']:v(row)
orig=Path('/workspace/engineering/pr306-original-cleanup-deterministic-control-owned/OWNERFINAL-original-cleanup-deterministic-control-v2.json')
o=json.loads(orig.read_bytes())
for row in o['bindings']:v(row)
def git(*a):return subprocess.check_output(['git','-C',str(R),*a])
assert git('rev-parse','HEAD').decode().strip()==x['head']
assert git('rev-parse','HEAD^{tree}').decode().strip()==x['tree']
assert git('status','--porcelain')==b''
proof=json.loads(Path('/workspace/engineering/captured-child-cleanup-independent-LIGHT-review/complete1422-independent-current-source-body-mode-proof-v2.json').read_bytes())
leaves={r.split(b'\t',1)[1].decode():r.split(b'\t',1)[0].split() for r in git('ls-tree','-r','-z','HEAD').split(b'\0') if r}
for row in proof['entries']:
 mode,kind,blob=leaves[row['path']];assert mode.decode()==row['mode'] and blob.decode()==row['blob']
 p=R/row['path'];st=p.lstat()
 if row['mode']=='120000':assert stat.S_ISLNK(st.st_mode);data=os.readlink(p).encode()
 else:assert stat.S_ISREG(st.st_mode);assert bool(st.st_mode & stat.S_IXUSR)==(row['mode']=='100755');data=p.read_bytes()
 assert len(data)==row['bytes'] and hashlib.sha256(data).hexdigest()==row['sha256']
 assert subprocess.check_output(['git','-C',str(R),'cat-file','blob',row['blob']])==data
assert len(leaves)==len(proof['entries'])==1422
body=Path('/workspace/engineering/captured-child-cleanup-configured-full-proposal/planned_toolkit_configured_full_body.py').read_text()
assert x['command']['argv'][-1]==body
A=ast.parse(body)
roots=[n for n in ast.walk(A) if isinstance(n,ast.Name) and n.id=='ROOT']
assert len(roots)==1 and isinstance(roots[0].ctx,ast.Load)
assert any(isinstance(n,ast.Name) and n.id=='root' and isinstance(n.ctx,ast.Store) for n in ast.walk(A))
assert not any(isinstance(n,(ast.ImportFrom,ast.Import)) and ('ROOT' in [a.name for a in n.names]) for n in ast.walk(A))
assert x['command']['argv'][4]=='set -euo pipefail\nsource "$1"\n"$2" "$3" "$4"\nshift 4\nexec "$@"\n'
assert x['command']['argv'][10:16]==['env','PYTEST_XDIST_AUTO_NUM_WORKERS=2','timeout','--signal=TERM','--kill-after=10s','600s']
assert x['command']['attempts']==1
assert not Path('/workspace/engineering/captured-child-cleanup-configured-full-once-owned').exists()
pre=Path('/workspace/engineering/captured-child-cleanup-configured-full-proposal/managed_activation_preflight.py').read_text();ast.parse(pre)
assert "len(expected)+1==19" in pre and "r=guards()" in pre
assert "['returncode']==0" in pre and ">=1200000000" in pre
assert "CLEANUP499_SERIALIZED_HEAVY_SLOT" in pre
assert "out.open('x')" in pre
patch=D/'canonical-standalone-inline-command-scope-proposed.patch'
patch.write_text('--- a/docs/skills/repository-operations.md\n+++ b/docs/skills/repository-operations.md\n@@\n+Treat each standalone `python -c` body as its own module scope. Bind names\n+used by preflight and origin checks inside that body; names imported by an\n+earlier shell preflight are unavailable to the later interpreter. Preserve a\n+refused proposal and freeze a named correction before granting execution.\n')
patch.chmod(0o600)
r={'schema':'independent-cleanup499-managed-full-proposal-review-v1','decision':'HOLD_UNDEFINED_ROOT_IN_STANDALONE_CONFIGURED_COMMAND','proposal':b(P),'head':x['head'],'tree':x['tree'],'source_clean':True,'checked':{'proposal_refs':len(x['bindings']),'LIGHT_refs':len(l['bindings']),'original_private_refs':len(o['bindings']),'Git_FS_mode_blob_entries':len(leaves),'exact_inline_body_matches_bound_snapshot':True,'static_ROOT_load_without_binding':True,'activation_exports':19,'preflight_before_Rcc_and_configured_task':True,'explicit_workers':2,'inner_TERM_seconds':600,'KILL_grace_seconds':10,'namespace_absent_at_review':True,'executed_launcher_preflight_RCC_tests_or_body':False},'blocker':{'category':'standalone_command_scope_NameError','evidence':'root=toolkit.REPOSITORY_ROOT assigns lowercase root; the first origin-loop code construction reads repr(str(ROOT)), with no ROOT definition or import. This blocks before any own-origin command or configured suite. Identical in frozen argv and bound planned body.','minimal_named_successor':'Replace this one ROOT load with root in a new immutable body and successor proposal; preserve original8324/2edee files unchanged. No source/test replay needed merely to establish corrected standalone binding.'},'execution_HOLD_after_correction':['Independent successor review and distinct root release','Root300 actual terminal returncode0 bound by exact path/hash','No concurrent heavy/gateway/install/actual and fresh capacity>=1200000000','Root-exclusive fresh0700 namespace and0600 auth/log/terminal; record actual result before postguard even on failure; no retry','Current source/input/helper/native references rehash and postguard readback; no native/private/browser/provider/release upgrade'],'Documentation_improvement':{'Canonical_file_changed_or_proposed':'docs/skills/repository-operations.md external exact four-line proposal; existing accepted ee804 activation lesson retained','Durable_learning_captured':'Separate standalone Python interpreters do not inherit Python names from shell preflight; preexecution command-scoping mistakes need named immutable correction.','Evidence':{'exact_delta':b(patch),'accepted_activation_delta':x['Documentation_improvement']['accepted_exact_canonical_delta'],'body':b('/workspace/engineering/captured-child-cleanup-configured-full-proposal/planned_toolkit_configured_full_body.py')},'Stale_or_ambiguous_guidance_removed':'A valid managed activation/preflight cannot make an undefined local name available in the separate configured command.','Remaining_uncertainty':'No command executed: NameError is a static source finding. Full suite/native/hosted readiness cause/unsampled failure cleanup remain unqualified.'},'Upstream_disposition':'none','bindings':x['bindings'],'constructor':b(__file__)}
out=D/'OWNERFINAL-independent-cleanup499-managed-full-proposal-HOLD.json'
with out.open('x') as f:json.dump(r,f,indent=2);f.write('\n')
out.chmod(0o600);print(json.dumps(b(out)))
