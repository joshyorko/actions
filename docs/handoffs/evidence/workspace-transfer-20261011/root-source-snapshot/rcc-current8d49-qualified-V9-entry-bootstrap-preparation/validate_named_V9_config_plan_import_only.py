"""Data-only plan assertion; no main/product/pytest/native call."""
import hashlib
import json
from pathlib import Path
import sys

BASE=Path(__file__).resolve().parent
assert Path(sys.prefix).resolve()==Path('/workspace/engineering/pr308/action_server/.venv').resolve()
import v9_entry_bootstrap
from owned_cache_policy_v8 import ROOTS,cache_plan,encoded,sha
import actual_transport_v8
import owned_native_entry_v9
import gateway_entry_v9
import launch_one_version_v9
import readonly_current_input_guard_v9
import managed_one_version_entry_v9

CFG=BASE/'FROZEN-current8d49-control3-qualified-V9-entry-config.json'
raw=CFG.read_bytes();assert hashlib.sha256(raw).hexdigest()=='e66d63863d1f2f2384bca32dec1e5bbf448e056b891a3d972689402d36646358'
cfg=json.loads(raw)
plan=cache_plan(cfg,'control3',actual_transport_v8.SOURCE,actual_transport_v8.TREE,actual_transport_v8.BINARIES)
assert sha(encoded(plan))=='1d0af9c61e34ed5e9ed20fb1a21a7240f59974ba8102c7de57141cfccae0da18'
assert ROOTS['control3']==cfg['owned_root']
assert not Path(cfg['owned_root']).exists() and not Path(cfg['owned_root']).is_symlink()
assert owned_native_entry_v9.main is actual_transport_v8.main
assert Path(actual_transport_v8.__file__).resolve()==Path('/workspace/engineering/rcc-current8d49-private-V8-real-fixture-mode-successor/actual_transport_v8.py')
forwarded=['--config',str(CFG),'--config-sha256',hashlib.sha256(raw).hexdigest(),'--release','/workspace/engineering/root-rcc-current8d49-control3-V9-one-release.json','--release-sha256','ROOT_UNGRANTED','--label','control3']
calls=gateway_entry_v9.gateway_plan(cfg,forwarded)
assert len(calls)==6 and calls[-1]==('action_server','run','python',str(BASE/'owned_native_entry_v9.py'),*forwarded)
pre,primary,post=launch_one_version_v9.commands(forwarded)
assert pre==post and '120s' in pre and '660s' in primary and str(BASE/'gateway_entry_v9.py') in primary
assert str(BASE/'readonly_current_input_guard_v9.py') in pre
print(json.dumps({'status':'PASS_REAL_PACKAGE_PYTHON_NAMED_V9_ALL_ENTRIES_AND_EXACT_CONFIG_PLAN_IMPORT_ONLY','entries_imported':6,'gateway_origin_commands_planned':5,'gateway_final_entry':'owned_native_entry_v9.py','root4_absent':True,'transport_main_product_native_pytest':'NOTRUN','budgets_unchanged':True}))
