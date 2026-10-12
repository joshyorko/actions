import ast,hashlib,json,stat
from pathlib import Path
D=Path('/workspace/engineering/pr312-shutdown-response-order-configured-full-proposal')
def bind(p):p=Path(p);return {'path':str(p),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'mode':oct(stat.S_IMODE(p.stat().st_mode))}
old=D/'OWNERFINAL-pr312-current77-managed-activation-configured-full-proposal-v2.json';r=json.loads(old.read_text());text=(D/'current77_readonly_guards_v2.py').read_text()
# Existing proposal hash-only bindings intentionally lack a byte-count cell.
replacements={' verify(proposal["helper_bindings"])':' assert binding(proposal["helper_bindings"]["path"])["sha256"]==proposal["helper_bindings"]["sha256"]',' verify(proposal["driver"]["frontend_lock"])':' assert binding(proposal["driver"]["frontend_lock"]["path"])["sha256"]==proposal["driver"]["frontend_lock"]["sha256"]'}
for before,after in replacements.items():assert text.count(before)==1;text=text.replace(before,after)
p=D/'current77_readonly_guards_v3.py';p.write_text(text);p.chmod(0o600);ast.parse(text)
for before,after in [('managed_activation_preflight_v2.py','managed_activation_preflight_v3.py'),('post_full_readonly_guards_v2.py','post_full_readonly_guards_v3.py')]:
 text=(D/before).read_text().replace('from current77_readonly_guards_v2 import','from current77_readonly_guards_v3 import');p=D/after;p.write_text(text);p.chmod(0o600);ast.parse(text)
r['schema']='actions-pr312-current77-managed-configured-full-NOEXECUTION/v3';r['command']['argv'][8]=str(D/'managed_activation_preflight_v3.py');r['command']['preflight']=bind(D/'managed_activation_preflight_v3.py');r['command']['post_argv'][1]=str(D/'post_full_readonly_guards_v3.py')
r['bindings'] += [bind(x) for x in (old,D/'current77_readonly_guards_v3.py',D/'managed_activation_preflight_v3.py',D/'post_full_readonly_guards_v3.py')]
r['named_successor'] += ' V3 corrects two hash-only input bindings to their actual original schema (helper-bindings/frontend-lock do not have bytes); V2 would otherwise raise KeyError before pytest. V1/V2 all immutable and NOTEXECUTED; no gating failure/result invented; body and budgets unchanged.'
r['constructor']=bind(__file__)
# Schema/read-only assertions before freezing. No guard import or execution.
original=json.loads(Path('/workspace/actions-cloud/receipts/pr305-runner/immutable-runner-proposal-v5.json').read_text())
for item in (original['helper_bindings'],original['driver']['frontend_lock']):assert 'bytes' not in item and bind(item['path'])['sha256']==item['sha256']
for item in r['bindings']:assert bind(item['path'])==item,item['path']
assert r['command']['argv'][-1]==Path(r['command']['exact_body']['path']).read_text()
assert not Path('/workspace/engineering/pr312-shutdown-response-order-configured-full-once-owned').exists()
p=D/'OWNERFINAL-pr312-current77-managed-activation-configured-full-proposal-v3.json'
with p.open('x') as f:json.dump(r,f,indent=2);f.write('\n')
p.chmod(0o600);print(json.dumps(bind(p)))
