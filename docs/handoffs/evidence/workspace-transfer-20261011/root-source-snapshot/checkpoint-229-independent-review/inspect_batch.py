from pathlib import Path
import hashlib,json,re,subprocess,collections,urllib.parse
R=Path('/workspace/engineering/campaign-checkpoint'); P='docs/program/evidence/wave11/current-engineering-20261011'; D=Path('/workspace/engineering/checkpoint-229-independent-review')
manifest=json.loads((R/P/'manifest.json').read_text());old=json.loads(subprocess.check_output(['git','-C',str(R),'show','HEAD:'+P+'/manifest.json']));assert len(manifest)==229 and len(old)==169 and all(manifest[k]==e for k,e in old.items())
checks=[];hits=[];urls=collections.Counter();new=sorted(set(manifest)-set(old))
patterns={'credential_token':r'(?i)(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{30,}|sk-[A-Za-z0-9]{20,}|AKIA[A-Z0-9]{16})','private_key':r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----','signed_url':r'(?i)[?&](?:x-amz-signature|sig|signature|token|access_token|se|sp)=','authorization_literal':r'(?i)Authorization[\s\"\x27:=]+Bearer\s+[A-Za-z0-9._-]{12,}'}
for name,e in manifest.items():
 p=R/P/name;assert p.resolve().is_relative_to((R/P).resolve()) and p.is_file() and not p.is_symlink()
 b=p.read_bytes();s=Path(e['source']);
 if s.is_file():assert s.read_bytes()==b
 else:assert name=='pr290-actual-integration.json' and name in old and e['source']=='authenticated GitHub merge and readback'
 assert len(b)==e['bytes'] and hashlib.sha256(b).hexdigest()==e['sha256']
 if name in old:assert subprocess.check_output(['git','-C',str(R),'show','HEAD:'+P+'/'+name])==b
 checks.append({'file':name,'source':str(s),'bytes':len(b),'sha256':e['sha256'],'prior_169_exact':name in old})
 if name not in new:continue
 text=b.decode('utf-8')
 if p.suffix=='.json':json.loads(text)
 for label,pattern in patterns.items():
  for m in re.finditer(pattern,text):hits.append({'file':name,'category':label,'byte_offset':m.start(),'matching_sha256':hashlib.sha256(m.group().encode()).hexdigest()})
 for m in re.finditer(r'https?://[^\s\"\x27<>]+',text):
  u=urllib.parse.urlsplit(m.group());urls[u.hostname]+=1
  if u.username or u.password:hits.append({'file':name,'category':'URL_credentials','byte_offset':m.start()})
 if p.suffix in ['.zip','.whl','.tar','.gz','.exe','.bin','.log','.jsonl']:raise AssertionError('new prohibited payload '+name)
assert not hits,hits
report={'manifest_entries':len(manifest),'prior_exact_immutable_entries':len(old),'new_entries':len(new),'all_local_original_source_bytes_lengths_SHA256_exact':True,'prior_authored_pr290_readback_provenance':'Historical manifest records authenticated GitHub merge/readback rather than local source path; original committed bytes and manifest unchanged','all_prior169_manifest_and_Gitbytes_preserved':True,'new_extensions':dict(collections.Counter(Path(n).suffix for n in new)),'secret_pattern_hits':hits,'new_URL_host_counts':dict(urls),'all_bindings':checks}
p=D/'verified-manifest-source-bindings.json';p.write_text(json.dumps(report,indent=2)+'\n'); print(json.dumps({k:v for k,v in report.items() if k!='all_bindings'}));print('OUTPUT_SHA',hashlib.sha256(p.read_bytes()).hexdigest())
