import ast,collections,hashlib,json,pathlib,re,stat,xml.etree.ElementTree as ET
P=pathlib.Path('/workspace/engineering/pr221-current-e2-inner-data-executor-successor-v2-PREPARATION');R=pathlib.Path('/workspace/engineering/pr221-current-e2-inner-v2-actual-controls-independent-review')
def bind(p):
 p=pathlib.Path(p);s=p.lstat();assert stat.S_ISREG(s.st_mode) and not p.is_symlink();h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return dict(path=str(p),bytes=s.st_size,sha256=h.hexdigest(),mode=oct(stat.S_IMODE(s.st_mode)))
p=P/'OWNERFINAL-original-current-e2-inner-v2-service-free-CONTROLS-actual-metadata-successor.json';d=json.loads(p.read_bytes());assert bind(p)['sha256']=='506e020ac4148234cb06f1c0ca8a6fca56cf08fc038a64c974964ddd0a76cccb'
for row in d['evidence']+[d['construction_metadata_successor']['predecessor']]:assert bind(row['path'])==row
cfg=json.loads((P/'frozen-service-free-control-inputs-v2.json').read_bytes());assert len(cfg['bindings'])==6
for row in cfg['bindings']:assert bind(row['path'])==row
manifest=json.loads((P/'frozen-executor-inputs.json').read_bytes());assert len(manifest['bindings'])==17
for row in manifest['bindings']:assert bind(row['path'])==row
originalinputs=json.loads((P/'frozen-service-free-control-inputs-v2.json').read_bytes());tests=ast.parse((P/'test_actual_inner_boundaries_v2.py').read_bytes());expected=set();groups={}
for n in tests.body:
 if not isinstance(n,ast.FunctionDef) or not n.name.startswith('test_'):continue
 values=None
 for dec in n.decorator_list:
  if isinstance(dec,ast.Call) and isinstance(dec.func,ast.Attribute) and dec.func.attr=='parametrize':values=ast.literal_eval(dec.args[1])
 names=[n.name] if values is None else [n.name+'['+str(v)+']' for v in values]
 expected.update(names);groups[n.name]=len(names)
assert len(expected)==50
owned=pathlib.Path(cfg['owned']);xml=ET.fromstring((owned/'junit.xml').read_bytes());cases=list(xml.iter('testcase'));observed={t.attrib['name'] for t in cases}
assert observed==expected and len(cases)==len(observed)==50
assert all(not list(t.iter('skipped')) and not list(t.iter('failure')) and not list(t.iter('error')) for t in cases)
outer=json.loads((P/'root-original-one-control-outer-terminal.json').read_bytes());plan=json.loads((P/'OWNERFINAL-current-e2-inner-successor-v2-service-free-CONTROL-PREEXECUTION.json').read_bytes());auth=json.loads((P/'ROOT-one-service-free-control-execution-authorization.json').read_bytes());term=json.loads((owned/'original-control-terminal.json').read_bytes())
assert outer['returncode']==0 and outer['argv']==plan['exact_parent_argv'] and 0<outer['elapsed_seconds']<135
assert term['returncode']==0 and term['post_bindings']=='PASS' and term['actual_original_inspection']=='NOT_RUN'
assert auth['proposal_binding']['sha256']==d['proposal_binding']['sha256'] and auth['independent_review_binding']['sha256']=='b318668ced8ea0acc62c666f0cb25449229070f52bceef3b24c119d20af31216'
summary=re.search(r'50 passed, 499 warnings in ([0-9.]+)s',(owned/'stdout.private.log').read_text());assert summary and float(summary.group(1))==40.87
inv=json.loads((P/'private-complete-one-control-output-file-inventory.json').read_bytes());assert len(inv['files'])==18
for row in inv['files']:assert bind(row['path'])==row
proof=dict(owner_binding=bind(p),declared_vs_actual_case_names_exact=True,case_name_set_sha256=hashlib.sha256(('\n'.join(sorted(expected))+'\n').encode()).hexdigest(),groups=groups,passed=50,unique=50,failed=0,errors=0,skips=0,warnings=499,pytest_seconds=40.87,outer_seconds=outer['elapsed_seconds'],outer_returncode=0,child_returncode=0,actual_launcher_before_finally_bindings=6,control_config_digest_checked_initially_only=True,additional_manifest_historical_bindings_rehashed_now=17,regular_owned_output_bindings_rehashed=18,post_bindings='PASS',artifact_inspection='NOT_RUN',no_replay_or_import=True)
f=R/'independent-original-control-complete-50-case-and-binding-proof.json';f.write_text(json.dumps(proof,indent=2,sort_keys=True)+'\n');f.chmod(0o400)
receipt=dict(schema='INDEPENDENT_CURRENT_E2_INNER_V2_ACTUAL_CONTROLS_REVIEW',decision='GO_CURRENT_E2_INNER_V2_ACTUAL_50_SERVICE_FREE_CONTROLS_ONLY',actual_control_owner_binding=bind(p),proof_binding=bind(f),executor_binding=plan['executor_binding'],control_binding=plan['control_binding'],proposal_binding=d['proposal_binding'],counts={k:proof[k] for k in ['passed','unique','failed','errors','skips','warnings']},scope='Original one synthetic real-function boundary control result only; no original aggregate artifact inspection, package import, install or native execution.',limits=['Six launcher cfg refs actually guarded before/finally, with config digest checked initially;17 executor historical refs were checked after controls and independently now, not relabeled original launcher guards.','Fifty cases exactly match source-derived parameter identities, including valid complete current217 baseline, individual restored RECORD/source poisons, read-spy header cap edges and actual entry guards.','Synthetic219/203/223 counts are baseline expectations, not observed original wheel/sdist counts.','Original015937/b1f executable HOLD and ef8ed/ccbb construction count mistakes retained; named17 correction changes metadata only.','Owner8-plan-ref guard label rejected; six actual guard rows + initial config hash distinguish from total8 plan evidence. No original code/control rerun.','18 owned regular-file bodies rehashed; no claim of a full all-type filesystem census from that file inventory.','Actual original artifact inspection requires separately reviewed proposal and distinct typed ROOT release.'],documentation_improvement={'Canonical_file_changed_or_proposed':'docs/skills/repository-operations.md; accept exact8 nonblank-line10bd lesson with precise contextual ZIP wording correction.','Exact_delta':'Replace proposed “Admit all archive headers before reading payloads” with “Admit all ZIP headers before reading payloads”; retain the remaining entry/baseline/source-authority lines.','Durable_learning_captured':'Real unoptimized/private-release admission and complete ZIP-header preflight require actual restored-baseline controls; sdist per-header validation and bounded gzip integrity are a separate mechanism.','Evidence':'Original50 JUnit case names exactly match11 frozen functions; actual0 terminals and499-warning log; new ZIP two-pass preflight, TAR per-member body validation and gzip full CRC/ISIZE source.','Stale_or_ambiguous_guidance_removed':'Avoid false all-TAR-header preflight claim; do not promote syntax, synthetic counts, or source mode diagnostics into artifact/content/consumer acceptance.','Remaining_uncertainty':'Original aggregate inner/source/generated-content authority and all consumer/native/release gates remain unobserved.'},upstream_disposition='none')
g=R/'OWNERFINAL-independent-original-current-e2-inner-v2-ACTUAL-50-controls-review.json';g.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n');g.chmod(0o400);print(json.dumps(bind(g)));print(json.dumps(bind(f)))
