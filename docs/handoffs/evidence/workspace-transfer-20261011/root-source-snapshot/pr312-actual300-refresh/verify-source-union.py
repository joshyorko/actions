import ast,hashlib,json,os,stat,subprocess
from pathlib import Path
R=Path('/workspace/engineering/runtime-checkout-eol');D=Path(__file__).parent
PARENT='77ed3de24f33412dff30e4e3c18841c4c09933ac';TARGET='e3c29cde8878307912e55ed09b6436c0f91d06d5'
def git(*a):return subprocess.check_output(['git','--no-optional-locks','-C',str(R),*a])
def bind(p):
 p=Path(p);z=p.read_bytes();return {'path':str(p),'bytes':len(z),'sha256':hashlib.sha256(z).hexdigest()}
pre=json.loads((D/'immutable-before-ordinary-merge-original77-and-target-e3c.json').read_text())
for row in pre['preserved_refs']:assert bind(row['path'])==row,row['path']
head=git('rev-parse','HEAD').decode().strip();staged=head==PARENT
if staged:
 assert git('rev-parse','MERGE_HEAD').decode().strip()==TARGET
 tree=git('write-tree').decode().strip()
else:
 assert git('show','--no-patch','--format=%P',head).decode().strip()==PARENT+' '+TARGET
 assert git('status','--porcelain')==b''
 tree=git('rev-parse','HEAD^{tree}').decode().strip()
assert tree==pre['prospective_tree']
a={x['path']:x for x in pre['original_entries']};b={x['path']:x for x in pre['target_entries']};entries=[];novel=[]
for line in git('ls-tree','-r','-z',tree).split(b'\0'):
 if not line:continue
 meta,name=line.split(b'\t');mode,kind,blob=meta.decode().split();name=name.decode();p=R/name;s=p.lstat();z=os.readlink(p).encode() if mode=='120000' else p.read_bytes()
 assert git('cat-file','blob',blob)==z and (mode=='120000' or bool(s.st_mode&0o111)==(mode=='100755')),name
 row=dict(path=name,mode=mode,kind=kind,blob=blob,bytes=len(z),sha256=hashlib.sha256(z).hexdigest());entries.append(row)
 if not any(x.get(name,{}).get('blob')==blob and x.get(name,{}).get('mode')==mode for x in (a,b)):novel.append(name)
assert set(x['path'] for x in entries)==set(a)|set(b)
assert sorted(novel)==['action_server/src/actions/server/_server.py','docs/skills/repository-operations.md'],novel
server='action_server/src/actions/server/_server.py';old=ast.parse(git('show',TARGET+':'+server));now=ast.parse((R/server).read_bytes())
findstart=lambda x:next(n for n in x.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name=='start_server')
ns=findstart(now);imp=next(n for n in ns.body if isinstance(n,ast.ImportFrom) and n.module=='fastapi');assert sum(x.name=='BackgroundTasks' for x in imp.names)==1;imp.names=[x for x in imp.names if x.name!='BackgroundTasks']
findshutdown=lambda x:next(n for n in ast.walk(x) if isinstance(n,ast.FunctionDef) and n.name=='shutdown')
nsh=findshutdown(ns);osh=findshutdown(findstart(old));assert nsh.args.args[0].arg=='background_tasks' and ast.dump(nsh.args.args[0].annotation)=="Name(id='BackgroundTasks', ctx=Load())";nsh.args.args.pop(0)
assert ast.dump(nsh.body[-1])==ast.dump(ast.parse('background_tasks.add_task(_thread.interrupt_main)').body[0]);nsh.body[-1]=osh.body[-1]
assert ast.dump(old)==ast.dump(now),'Merged whole server differs from target beyond original BackgroundTasks shutdown change'
# Both accepted canonical patches must still apply in reverse: exact source lesson is retained;
# incoming target guide is represented by the automatic three-way union with no manual changes.
patch=Path('/workspace/engineering/pr312-shutdown-response-order-source/exact-canonical-response-order-and-client-completion.patch')
added=[]
for l in patch.read_text().splitlines():
 if l.startswith('+') and not l.startswith('+++'):added.append(l[1:])
block='\n'.join(added);assert block in (R/'docs/skills/repository-operations.md').read_text()
proof={'status':'PASS_COMPLETE_ORDINARY_UNION_SOURCE_AND_ALL_RETAINED_REFS','head':head,'tree':tree,'ordered_parents':[PARENT,TARGET],'source_entries':entries,'complete_count':len(entries),'original_count':len(a),'target_count':len(b),'no_deleted_parent_paths':True,'novel_paths':novel,'all_other_leaves_modes_match_a_parent':len(entries)-len(novel),'whole_target_server_AST_exact_after_original_two_shutdown_changes_normalized':True,'original_seven_EOLog_paths_body_modes_from_parent_exact':True,'automatic_guide_union_preserves_exact_source_shutdown_canonical_block':True,'retained_original_ref_count':len(pre['preserved_refs']),'clean':not staged,'original_fullproposal_NOT_RUN':True,'upstream_disposition':'none'}
out=D/('before-commit-complete-union-proof.json' if staged else 'committed-complete-union-proof.json');assert not out.exists();out.write_text(json.dumps(proof,indent=2)+'\n');out.chmod(0o600);print(json.dumps({'proof':bind(out),'leaves':len(entries),'other_parent_exact':len(entries)-len(novel),'tree':tree}))
