from pathlib import Path
import os,stat,json,hashlib,ast,xml.etree.ElementTree as ET
P=Path('/workspace/engineering/completed8d49-two-root-storage-PREPARATION');D=Path(__file__).parent

def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def bind(p):
 p=Path(p);return {'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p),'mode':oct(p.stat().st_mode&0o777)}
def save(path,text):
 assert not path.exists();path.write_text(text);os.chmod(path,0o444)
a=ast.parse((P/'guard_readonly.py').read_text());nodes=[n for n in a.body if isinstance(n,(ast.Import,ast.ImportFrom)) or isinstance(n,ast.FunctionDef) and n.name in ('sha','inventory','_snapshot')];ns={};exec(compile(ast.Module(body=nodes,type_ignores=[]),'readonly_snapshot_defs','exec'),ns)
baseconfig=P/'private-exact-two-root-inputs.json';base=json.loads(baseconfig.read_text());roots=base['roots'].copy();snaps=base['selected_snapshots'].copy();roots['original27-log']=roots.pop('robocorp-log');snaps['original27-log']=snaps.pop('robocorp-log')
parent=Path('/workspace/engineering/rcc-current8d49-private-V8-fixture-logger-successor');newroots={};completions=[];records=[]
for label,d,prefix,passed in [('fixture42-GREEN-log','pure-fixture-logger-GREEN-owned-once','original-GREEN',42),('fixture51-TEMPORAL-log','pure-fixture-logger-GREEN-TEMPORAL-owned-once','original-GREEN-TEMPORAL',51)]:
 root=parent/d/'robocorp-log';terminal=parent/d/(prefix+'-terminal.json');log=parent/d/(prefix+'.private.log');xml=parent/d/(prefix+'-junit.xml');tj=json.loads(terminal.read_text());x=ET.parse(xml).getroot();cases=x.findall('.//testcase');assert len(cases)==passed and not x.findall('.//failure') and not x.findall('.//error') and not x.findall('.//skipped');assert tj['returncode']==0 and '--robocorp-log-output='+str(root) in tj['argv']
 for p in [terminal,log,xml]:completions.append(bind(p))
 snapshot=json.loads(json.dumps(ns['_snapshot'](root)));assert snapshot==json.loads(json.dumps(ns['_snapshot'](root)));s=root.lstat();assert stat.S_ISDIR(s.st_mode) and not root.is_symlink() and s.st_uid==s.st_gid==1000 and stat.S_IMODE(s.st_mode)==0o700
 snapshot['allocated_bytes']=s.st_blocks*512+sum(p.lstat().st_blocks*512 for p in root.rglob('*'));snapshot['hardlink_groups']=0
 newroots[label]={'path':str(root),'snapshot':snapshot};records.append({'label':label,'terminal':bind(terminal),'junit':bind(xml),'stdout':bind(log),'passed':passed,'actual_native':'NOT_RUN'})
for n,p in roots.items():assert json.loads(json.dumps(ns['_snapshot'](Path(p))))=={k:v for k,v in snaps[n].items() if k in ('root','entries','identities')}
allroots={**roots,**{k:v['path'] for k,v in newroots.items()}};assert len(set(allroots.values()))==4
qualified=Path('/workspace/engineering/rcc-current8d49-qualified-V8-config-preparation/FROZEN-current8d49-control3-qualified-V8-config.json');q=json.loads(qualified.read_text());overlaps=[];rows=0
def walk(v):
 global rows
 if isinstance(v,dict):
  if isinstance(v.get('path'),str) and ('sha256' in v or 'bytes' in v):
   rows+=1
   if any(Path(v['path'])==Path(p) or Path(v['path']).is_relative_to(Path(p)) for p in allroots.values()):overlaps.append(v['path'])
  for e in v.values():walk(e)
 elif isinstance(v,list):
  for e in v:walk(e)
walk(q);walk(base['completion_bindings']);walk(base['references']);walk(completions);assert not overlaps
sup={'schema':'EXACT_FOUR_COMPLETED8D49_ROOTS_BY_IMMUTABLE_PREDECESSOR_AND_TWO_LOG_ADDITIONS','base_config_binding':bind(baseconfig),'base_owner_binding':bind(P/'OWNERFINAL-two-completed8d49-roots-capped-storage-PREEXECUTION.json'),'base_rename':{'robocorp-log':'original27-log'},'added_roots':newroots,'completion_bindings':completions,'completion_records':records,'qualified_current_config_binding':bind(qualified),'scanned_current_config_rows':rows,'critical_ordinary_row_overlap':False,'capacity_now':{p:os.statvfs(p).f_bavail*os.statvfs(p).f_frsize for p in ['/workspace','/tmp','/dev/shm']},'selected_allocated_bytes':sum(s['allocated_bytes'] for s in snaps.values())+sum(v['snapshot']['allocated_bytes'] for v in newroots.values())}
S=D/'private-four-root-input-supplement.json';save(S,json.dumps(sup,indent=2)+'\n')
loader='''def load_config(path):
    supplement=json.loads(Path(path).read_bytes())
    row=supplement['base_config_binding'];p=Path(row['path'])
    assert p.is_file() and not p.is_symlink() and p.stat().st_size==row['bytes']
    assert sha(p)==row['sha256'] and oct(stat.S_IMODE(p.stat().st_mode))==row['mode']
    config=json.loads(p.read_bytes())
    config['roots']['original27-log']=config['roots'].pop('robocorp-log')
    config['selected_snapshots']['original27-log']=config['selected_snapshots'].pop('robocorp-log')
    for label,record in supplement['added_roots'].items():
        assert label not in config['roots']
        config['roots'][label]=record['path'];config['selected_snapshots'][label]=record['snapshot']
    config['completion_bindings']+=supplement['completion_bindings']
    config['references']+=[supplement['qualified_current_config_binding'],supplement['base_owner_binding']]
    config['completion_records_extra']=supplement['completion_records']
    assert len(config['roots'])==len(set(config['roots'].values()))==4
    return config
'''
arch=(P/'archive_exact_two_completed_roots_once.py').read_text();t=ast.parse(arch);lines=arch.splitlines(True)
assigns={'DEST':"Path('/tmp/actions-completed8d49-four-root-preserved-v2')",'STAGE':"Path('/tmp/actions-completed8d49-four-root-preservation-stage-v2')",'NAMES':repr(list(allroots)),'_INDEX_MAGIC':repr('EXACT_FOUR_COMPLETED8D49_OWNED_ROOTS_ALL_STAGED_BEFORE_REMOVAL'),'_COMPLETION_CONFIG':"Path("+repr(str(S))+")",'_COMPLETION_BINDING':repr(bind(S))}
for n in sorted([n for n in t.body if isinstance(n,ast.Assign) and len(n.targets)==1 and isinstance(n.targets[0],ast.Name) and n.targets[0].id in assigns],key=lambda n:n.lineno,reverse=True):lines[n.lineno-1:n.end_lineno]=[n.targets[0].id+' = '+assigns[n.targets[0].id]+'\n']
arch=''.join(lines).replace('config = json.loads(_COMPLETION_CONFIG.read_bytes())','config = load_config(_COMPLETION_CONFIG)')
arch=arch.replace('root.name in _ROOT_SNAPSHOTS','_key_for_root(root) in _ROOT_SNAPSHOTS').replace('_root(root.name)','_root(_key_for_root(root))').replace('_ROOT_SNAPSHOTS[root.name]','_ROOT_SNAPSHOTS[_key_for_root(root)]').replace('_STAGE_RECORDS[root.name]','_STAGE_RECORDS[_key_for_root(root)]').replace("root.name + '.tar.gz'","_key_for_root(root) + '.tar.gz'").replace(", root.name, _ROOT_SNAPSHOTS",", _key_for_root(root), _ROOT_SNAPSHOTS")
more=loader+'''\ndef _key_for_root(root):
    config=load_config(_COMPLETION_CONFIG)
    matching=[key for key,value in config['roots'].items() if Path(value)==root]
    assert len(matching)==1
    return matching[0]
'''
arch=arch.replace('def _root(name):',more+'\ndef _root(name):',1)
extra='''    for record in config['completion_records_extra']:
        terminal=json.loads(Path(record['terminal']['path']).read_bytes())
        assert terminal['returncode']==0
        assert '--robocorp-log-output='+config['roots'][record['label']] in terminal['argv']
'''
arch=arch.replace('    name = next(n for n,p in config',extra+'    name = next(n for n,p in config',1)
af=D/'archive_exact_four_completed_roots_once.py';save(af,arch);ast.parse(arch)
guard=(P/'guard_readonly.py').read_text().replace('def exact(row):',loader+'\ndef exact(row):',1).replace('assert root.name==name and root.is_dir()','assert root.name==Path(path).name and root.is_dir()').replace("'roots':2","'roots':4")
guard=guard.replace(" assert green['returncode']==0\n", " assert green['returncode']==0\n for record in config['completion_records_extra']:\n  terminal=json.loads(Path(record['terminal']['path']).read_bytes());assert terminal['returncode']==0 and '--robocorp-log-output='+config['roots'][record['label']] in terminal['argv']\n")
gf=D/'guard_readonly.py';save(gf,guard);ast.parse(guard)
driver=(P/'launch_once.py').read_text();t=ast.parse(driver);lines=driver.splitlines(True);bindings={'archiver':bind(af),'guard':bind(gf),'config':bind(S)}
reps={'OWNED':"Path('/workspace/engineering/root-completed8d49-four-root-storage-one-owned-v2')",'PROPOSAL':"HERE / 'OWNERFINAL-four-completed8d49-roots-capped-storage-PREEXECUTION-v2.json'",'ROOT_RELEASE':"Path('/workspace/engineering/root-completed8d49-four-root-storage-reviewed-release-v2.json')",'EXPECTED_REVIEW_DECISION':repr('GO_EXACT_FOUR_COMPLETED8D49_ROOTS_CAPPED_STORAGE_PREEXECUTION'),'CONFIG':"HERE / 'private-four-root-input-supplement.json'",'ARCHIVER':"HERE / 'archive_exact_four_completed_roots_once.py'",'BINDINGS':repr(bindings)}
for n in sorted([n for n in t.body if isinstance(n,ast.Assign) and len(n.targets)==1 and isinstance(n.targets[0],ast.Name) and n.targets[0].id in reps],key=lambda n:n.lineno,reverse=True):lines[n.lineno-1:n.end_lineno]=[n.targets[0].id+' = '+reps[n.targets[0].id]+'\n']
driver=''.join(lines).replace('ROOT_ONE_EXACT_TWO_COMPLETED8D49_STORAGE_RELEASE','ROOT_ONE_EXACT_FOUR_COMPLETED8D49_STORAGE_RELEASE').replace('--root-execute-reviewed-two-completed8d49-roots','--root-execute-reviewed-four-completed8d49-roots').replace("config = json.loads(CONFIG.read_bytes())","config = guard['load_config'](CONFIG)").replace('/tmp/actions-completed8d49-two-root-preserved','/tmp/actions-completed8d49-four-root-preserved-v2').replace('/tmp/actions-completed8d49-two-root-preservation-stage','/tmp/actions-completed8d49-four-root-preservation-stage-v2')
df=D/'launch_once.py';save(df,driver);ast.parse(driver)
# Read-only selected/completion functions, no driver/source-env/archive invocation.
parsed=ast.parse(guard);gg={};exec(compile(ast.Module(body=[n for n in parsed.body if isinstance(n,(ast.Import,ast.ImportFrom,ast.FunctionDef))],type_ignores=[]),'four_root_readonly_controls','exec'),gg);loaded=gg['load_config'](S);result=gg['selected_roots'](loaded);assert result['roots']==4
print(json.dumps({'selected_members':sum(len(s['entries']) for s in loaded['selected_snapshots'].values()),'allocated_bytes':sup['selected_allocated_bytes'],'read_only_four_root_check':'PASS','archive_and_removal':'NOT_RUN','config_bytes':S.stat().st_size,'current_config_overlap':False}))
