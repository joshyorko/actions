import hashlib,json,os,re,stat,subprocess,tarfile
from pathlib import Path
import xml.etree.ElementTree as ET

BASE=Path('/workspace/engineering/pr308-native-home-mode-current-a54-SOURCE-LIGHT');ROOT=Path('/workspace/engineering/pr308');OUT=Path(__file__).resolve().parent
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb')as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def bind(p):
 p=Path(p);return dict(path=str(p),bytes=p.stat().st_size,sha256=sha(p))
def check(row):
 p=Path(row['path']);assert p.stat().st_size==row['bytes']and sha(p)==row['sha256']and oct(stat.S_IMODE(p.stat().st_mode))==row['mode']
owner=BASE/'OWNERFINAL-current396925-public-native-home-mode-and-a54-union-SOURCE_LIGHT.json'
assert owner.stat().st_size==15663 and sha(owner)=='7fe036c7ea9a42e5c652c2f33726a0a6d8d4964de4a007eb2a0e680eeef0f489'
p=json.loads(owner.read_bytes())
for row in p['frozen_bindings']:check(row)
assert len(p['frozen_bindings'])==33
cfg=json.loads(Path('/workspace/engineering/rcc-compatibility-current-e4ff-qualified-config-successor/FROZEN-current-e4ff-control3-owned-cache-SOURCE-QUALIFIED-v4.json').read_bytes())
before=json.loads((BASE/'current-readonly-before-retention-proof.json').read_bytes());after=json.loads((BASE/'current-readonly-after-retention-proof.json').read_bytes())
assert before['source']==after['source']=='e4ff080375a8422bb656e52d218f198521dda078'
assert before['current_source']==after['current_source']==p['source']['commit']
alias=before['historical_failed_alias'][0];assert alias==after['historical_failed_alias'][0];check(alias['archive'])
old_receipt=Path(alias['original_binding']['path']);assert not old_receipt.exists()
# Read exactly the authorized archived original receipt; do not extract payloads.
with tarfile.open(alias['archive']['path'],'r|gz')as tar:
 found=None
 for member in tar:
  if member.name==alias['member']:
   assert member.isfile()and member.size==alias['original_binding']['bytes']and oct(member.mode)==alias['original_binding']['mode']
   found=tar.extractfile(member).read();break
 assert found is not None and hashlib.sha256(found).hexdigest()==alias['original_binding']['sha256']
 assert json.loads(found)['status']=='FAIL'
fixture=ROOT/'action_server/tests/action_server_tests/test_source_staging_rcc_consumer.py'
current_exact=historical=archived=0
for row in cfg['bindings']:
 path=Path(row['path'])
 if path==old_receipt:
  assert row==alias['original_binding'];archived+=1
 elif path==fixture:
  body=subprocess.check_output(['git','-C',str(ROOT),'show',cfg['source']+':'+path.relative_to(ROOT).as_posix()]);assert len(body)==row['bytes']and hashlib.sha256(body).hexdigest()==row['sha256'];historical+=1
 else:check(row);current_exact+=1
assert (len(cfg['bindings']),current_exact,historical,archived)==(237,235,1,1)
rows=json.loads((BASE/'private-current396925-complete-source-body-mode-inventory.json').read_bytes())
assert len(rows)==1426
prior=json.loads(Path('/workspace/engineering/pr308-current3969-independent-source-union-review/private-current3969-complete-source-Git-FS-body-mode-inventory.json').read_bytes())
expected={r['path']:r for r in prior}
for row in rows:
 baseline=expected[row['path']]
 for k in ('mode','blob','bytes','sha256','fs_mode'):assert row[k]==baseline[k]
 path=ROOT/row['path'];body=os.readlink(path).encode()if row['mode']=='120000'else path.read_bytes();assert hashlib.sha256(body).hexdigest()==row['sha256']and stat.S_IMODE(path.lstat().st_mode)==row['fs_mode']
native=Path(cfg['native_original_root']);assert len(cfg['native_original_members'])==1192
assert {x.relative_to(native).as_posix()for x in native.rglob('*')}=={r['path']for r in cfg['native_original_members']}
for row in cfg['native_original_members']:
 path=native/row['path'];assert stat.S_IMODE(path.lstat().st_mode)==row['mode']
 if row['kind']=='file':assert not path.is_symlink()and sha(path)==row['content_sha256']
 elif row['kind']=='directory':assert path.is_dir()and not path.is_symlink()
 else:assert os.readlink(path)==row['link_target']
reuse=json.loads((BASE/'own-current30-input-and-five-concrete-origins-Bootstrap-reuse.json').read_bytes());assert len(reuse['inputs'])==30 and len(reuse['origins'])==5
for name,digest in reuse['inputs'].items():assert sha(ROOT/name)==digest
assert sha(reuse['original_bootstrap_log'])==reuse['original_bootstrap_log_sha256']
for origin in reuse['origins']:
 assert Path(origin['prefix']).resolve().is_relative_to(ROOT)and Path(origin['origin']).resolve().is_relative_to(ROOT)and Path(origin['origin']).is_file()
cases=list(ET.fromstring((BASE/'current-scoped-source-junit.xml').read_bytes()).iter('testcase'))
assert len(cases)==len({(c.attrib['classname'],c.attrib['name'])for c in cases})==268
assert sum(c.find('skipped')is not None for c in cases)==1
assert not any(c.find('failure')is not None or c.find('error')is not None for c in cases)
cache=[c for c in cases if c.attrib['name'].startswith('test_owned_rcc_package_cache')];assert len(cache)==47 and not any(c.find('skipped')is not None for c in cache)
shutdown=[c for c in cases if c.attrib['classname'].endswith('test_shutdown_response_order')];assert len(shutdown)==10
log=(BASE/'current396925-cached-LIGHT-original.private.log').read_text();assert re.search(r'96 passed',log)and re.search(r'267 passed, 1 skipped, 3 deselected, 5 warnings in 13.67s',log)
terminal=json.loads((BASE/'current396925-cached-LIGHT-terminal.json').read_bytes());assert terminal['status']=='PASS'and[record['returncode']for record in terminal['records']]==[0,0,0]
producer=json.loads((BASE/'typed-current-producer-and-five-selected-inventory.json').read_bytes());assert(producer['current_producer_count'],producer['original_producer_count'],producer['match'],len(producer['changed']),len(producer['added']),producer['deleted'],producer['five_selector_changes'])==(275,268,260,8,7,[],[])
yaml=json.loads((BASE/'current-generator8-allYAML30-roundtrip.json').read_bytes());assert yaml['generated_output_count']==8 and yaml['tracked_YAML_total']==30
for path,digest in yaml['all30_bytes_sha256'].items():assert sha(ROOT/path)==digest
assert subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD','HEAD^{tree}']).decode().splitlines()==[p['source']['commit'],p['source']['tree']]
assert not subprocess.check_output(['git','-C',str(ROOT),'status','--porcelain'])
result={'status':'PASS_READ_ONLY_CURRENT3969_FROZEN_LIGHT_AND_RETENTION','owner':bind(owner),'source':p['source'],'owner_refs_verified':33,'historical_refs':{'current_exact':235,'original_fixture_Git_exact':1,'failed_archived_receipt_exact':1,'original_archived_status':'FAIL','whole_archives_not_extracted':True},'source1426_body_modes_exact':True,'native1192_body_modes_member_set_exact':True,'prepared30_exact':True,'existing_five_concrete_origins_bound_no_import_replay':True,'scoped_unique_nodes':268,'passed':267,'skipped':1,'deselected':3,'permanent_cache_controls':47,'shutdown_controls':10,'Toolkit_passed':96,'producer_scope':[275,268,260,8,7],'selected_inputs_separate_unchanged':5,'generation8_YAML30_exact':True,'pytest38_recovery':'Absent accordingROOT; no recoveryreceipt inferred or admitted here.','no_tests_constructor_guard_import_gateway_native_execution':True}
q=OUT/'independent-current3969-SOURCE-LIGHT-readonly-proof.json'
with q.open('x')as f:json.dump(result,f,indent=2,sort_keys=True);f.write('\n')
q.chmod(0o600);print(json.dumps(bind(q)))
