import ast
import copy
import hashlib
import json
import re
from pathlib import Path
import stat
import subprocess

R = Path('/workspace/engineering/rcc-current-e4ff-cache-mode-private-v8-proposal')
ROOT = Path('/workspace/engineering/pr308')
OUT = Path(__file__).resolve().parent
def bind(p):
    p=Path(p);b=p.read_bytes()
    return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest(),mode=oct(stat.S_IMODE(p.stat().st_mode)))
owner=R/'OWNERFINAL-PUBLIC-current-e4ff-native-managed-home-mode-fixture-and-guide-patch.json'
assert bind(owner)['sha256']=='a5de4819d2a1458cdd331dd387daccd22f4101ef510e29328de5d17e3d840107'
p=json.loads(owner.read_bytes())
for row in p['bindings']:
    got=bind(row['path'])
    assert got['bytes']==row['size_bytes'] and got['sha256']==row['sha256'] and got['mode']==row['mode']
assert subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD','HEAD^{tree}']).decode().splitlines()==[p['source']['head'],p['source']['tree']]
assert not subprocess.check_output(['git','-C',str(ROOT),'status','--porcelain'])
patch=(R/'PUBLIC-e4ff-native-managed-home-mode-fixture-and-guide-proposed.patch').read_text()
# Reconstruct both proposed files entirely in memory, without applying a patch.
sections=re.split(r'(?m)^--- a/',patch)[1:]
assert len(sections)==2
derived={}
for section in sections:
    lines=section.splitlines(True);path=lines[0].strip()
    assert lines[1].strip()=='+++ b/'+path
    original=(ROOT/path).read_text().splitlines(True);result=[];cursor=0;i=2
    while i<len(lines):
        header=re.fullmatch(r'@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@\n',lines[i]);assert header
        start=int(header[1])-1;assert start>=cursor
        result.extend(original[cursor:start]);cursor=start;i+=1
        old_count=new_count=0
        while i<len(lines) and not lines[i].startswith('@@ '):
            line=lines[i];assert line[0] in ' +-'
            if line[0] in ' -':
                assert original[cursor]==line[1:];cursor+=1;old_count+=1
            if line[0] in ' +':result.append(line[1:]);new_count+=1
            i+=1
        assert old_count==int(header[2] or 1) and new_count==int(header[4] or 1)
    result.extend(original[cursor:]);derived[path]=''.join(result)
fixture='action_server/tests/action_server_tests/test_source_staging_rcc_consumer.py'
guide='docs/skills/repository-operations.md'
assert set(derived)=={fixture,guide}
assert derived[fixture].encode()==(R/'proposed_test_source_staging_rcc_consumer_v2.py').read_bytes()
old=ast.parse((ROOT/fixture).read_bytes());new=ast.parse(derived[fixture])
names=[n.name for n in new.body if isinstance(n,ast.FunctionDef) and n.name.startswith('test_owned_rcc_package_cache_native_home_')]
assert len(names)==3
oh=next(n for n in old.body if isinstance(n,ast.FunctionDef) and n.name=='_prepare_owned_rcc_test_package_cache')
nh=next(n for n in new.body if isinstance(n,ast.FunctionDef) and n.name==oh.name)
i=next(i for i,n in enumerate(nh.body) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='client_metadata' for t in n.targets))
assert ast.dump(nh.body[i],include_attributes=False)==ast.dump(ast.parse('client_metadata = client.stat()').body[0],include_attributes=False)
assert ast.dump(nh.body[i+1],include_attributes=False)==ast.dump(ast.parse('assert stat.S_IMODE(client_metadata.st_mode) in (0o700, 0o750) and client_metadata.st_uid == os.getuid() and client_metadata.st_gid == os.getgid(), "PACKAGE_CACHE_CLIENT_MODE_OWNER"').body[0],include_attributes=False)
nh.body.pop(i)
oi=next(i for i,n in enumerate(oh.body) if isinstance(n,ast.Assert) and isinstance(n.msg,ast.Constant) and n.msg.value=='PACKAGE_CACHE_CLIENT_MODE_OWNER')
nh.body[oi]=copy.deepcopy(oh.body[oi])
new.body=[n for n in new.body if not(isinstance(n,ast.FunctionDef) and n.name in names)]
assert ast.dump(old,include_attributes=False)==ast.dump(new,include_attributes=False)
def cases(module,names):
    total=0
    for n in module.body:
        if isinstance(n,ast.FunctionDef) and n.name in names:
            count=1
            for dec in n.decorator_list:
                if isinstance(dec,ast.Call) and isinstance(dec.func,ast.Attribute) and dec.func.attr=='parametrize':count*=len(ast.literal_eval(dec.args[1]))
            total+=count
    return total
oldnames=[n.name for n in old.body if isinstance(n,ast.FunctionDef) and n.name.startswith('test_owned_rcc_package_cache')]
assert cases(old,oldnames)==34 and cases(ast.parse(derived[fixture]),names)==13
astproof=json.loads((R/'PUBLIC-exact-e4ff-fixture-guide-AST-preservation-proof.json').read_bytes())
addition='\n'+'\n'.join(astproof['documentation']['exact_inserted_lines'])+'\n'
anchor=astproof['documentation']['anchor']+'\n'
text=(ROOT/guide).read_text();assert text.count(anchor)==1 and text.replace(anchor,anchor+addition)==derived[guide]
logs={}
for label,name in [('RED','corrected-V7-e4-mode-source-RED.private.log'),('GREEN','final-V8-public-private-mode-source-GREEN.private.log')]:
    text=(R/name).read_text();count=re.search(r'Ran (\d+) tests? in ([\d.]+)s',text)
    nodes=re.findall(r'^(test_\S+).*? \.\.\. (ok|FAIL|ERROR)$',text,re.M)
    logs[label]={'binding':bind(R/name),'cases':int(count[1]),'seconds':float(count[2]),'terminal_counts':{k:sum(v==k for _,v in nodes) for k in ['ok','FAIL','ERROR']},'public0750':next(v for n,v in nodes if n=='test_public0750_cold_warm')}
assert logs['RED']['cases']==7 and logs['RED']['terminal_counts']=={'ok':0,'FAIL':2,'ERROR':5} and logs['RED']['public0750']=='FAIL'
assert logs['GREEN']['cases']==68 and logs['GREEN']['terminal_counts']=={'ok':68,'FAIL':0,'ERROR':0} and logs['GREEN']['public0750']=='ok'
assert subprocess.run(['git','-C',str(ROOT),'apply','--check',str(R/'PUBLIC-e4ff-native-managed-home-mode-fixture-and-guide-proposed.patch')],capture_output=True).returncode==0
assert not subprocess.check_output(['git','-C',str(ROOT),'status','--porcelain'])
result={'status':'PASS_READ_ONLY_PUBLIC_PATCH_AST_BYTES_BINDINGS_AND_ORIGINAL_EVIDENCE','source':p['source'],'owner':bind(owner),'bound_refs':26,'whole_original_AST_exact_except_one_predicate':True,'original_permanent_cases':34,'new_permanent_functions':names,'new_cases':13,'patch_reconstructed_in_memory':True,'only_paths':[fixture,guide],'guide_other_bytes_exact':True,'guide_inserted_lines':9,'patch_apply_check':True,'original_logs':logs,'no_constructor_import_test_guard_native_or_gateway_execution':True}
q=OUT/'independent-public-patch-readonly-proof.json'
with q.open('x') as stream:json.dump(result,stream,indent=2,sort_keys=True);stream.write('\n')
q.chmod(0o600);print(json.dumps(bind(q)))
