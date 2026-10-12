"""Root-supplied accepted binding constructor; no test/RCC/native execution."""
import hashlib,json,os,stat,subprocess,sys
from pathlib import Path
O=Path(__file__).parent;assert len(sys.argv)==2
adopt=Path(sys.argv[1]);receipt=json.loads(adopt.read_text())
assert receipt['status']=='ROOT_ADOPTED_EDF_SOURCE_AND_ACCEPTED_STORAGE_BINDINGS'
cfg=json.loads((O/'expectedEDF-source-gates-UNBOUND-template.json').read_text());R=Path(cfg['source_root'])
assert receipt['source'] and len(receipt['source'])==40 and receipt['tree']==cfg['tree']
def binding(p):
 p=Path(p);b=p.read_bytes();return {'path':str(p),'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b),'mode':oct(stat.S_IMODE(p.stat().st_mode))}
def check(row):assert binding(row['path'])==row
for group in ['root_source_adoption','accepted_B28_actual_and_independent','accepted_TMP_relocation_actual_and_independent']:
 assert receipt[group] and type(receipt[group]) is list
 for row in receipt[group]:check(row)
 cfg[group if group!='root_source_adoption' else 'root_current_source_adoption']=receipt[group]
assert subprocess.check_output(['git','-C',str(R),'rev-parse','HEAD','HEAD^{tree}']).decode().splitlines()==[receipt['source'],receipt['tree']]
assert not subprocess.check_output(['git','-C',str(R),'status','--porcelain'])
raw=subprocess.check_output(['git','-C',str(R),'ls-tree','-r','-z',receipt['source']]);rows=[]
for item in raw.split(b'\0'):
 if not item:continue
 info,path=item.split(b'\t',1);mode,kind,obj=info.decode().split();p=R/path.decode();b=os.readlink(p).encode() if mode=='120000' else p.read_bytes();committed=subprocess.check_output(['git','-C',str(R),'cat-file','blob',obj]);assert b==committed
 rows.append({'path':path.decode(),'mode':mode,'object':obj,'sha256':hashlib.sha256(b).hexdigest(),'fs_mode':stat.S_IMODE(p.lstat().st_mode)})
assert len(rows)==1440
p=O/'private-currentEDF-source-body-mode-inventory.json';assert not p.exists();p.write_text(json.dumps(rows,indent=2)+'\n');p.chmod(0o400)
cfg.update(head=receipt['source'],source_inventory=str(p),execution_enablement='ROOT_CURRENT_SOURCE_GATES_ADOPTED_ONCE',phase='LIGHT',pytest_owned_parent=receipt['pytest_LIGHT_owned_parent'],owned_evidence_root=receipt['LIGHT_owned_evidence_root'])
cfg['expected_tracked_YAML_count']=len(subprocess.check_output(['git','-C',str(R),'ls-files','.github/*.yaml','.github/*.yml']).decode().splitlines())
cfg['implementation_bindings']=[binding(O/x) for x in ['currentEDF_readonly_source_and_storage_guard.py','currentEDF_cached_source_LIGHT_body.py','launch_currentEDF_source_gate_once.py','currentEDF_configured_full_body.py']]+[binding(p)]
final=O/'frozen-currentEDF-source-LIGHT-inputs.json';assert not final.exists();final.write_text(json.dumps(cfg,indent=2,sort_keys=True)+'\n');final.chmod(0o400)
print(json.dumps({'status':'SOURCE_LIGHT_CONFIG_CONSTRUCTED_FOR_REVIEW_ONLY','config':binding(final),'source':cfg['head'],'tree':cfg['tree'],'source_count':len(rows),'native':'NOT_RUN','root_execution_release':'SEPARATELY_REQUIRED'}))
