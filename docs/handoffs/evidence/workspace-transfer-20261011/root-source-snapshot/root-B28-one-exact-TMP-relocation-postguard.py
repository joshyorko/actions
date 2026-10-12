import hashlib, json, sys, os, stat
from pathlib import Path
assert not sys.flags.optimize
script=Path('/workspace/engineering/capacity-recovery-B28-one-exact-TMP-relocation-source/relocate_one.py')
raw=script.read_bytes()
assert hashlib.sha256(raw).hexdigest()=='d6d6aedf6c4760eb0afaa40978627137ea15fc63f87cd365aa53ddf283983c8f'
module={'__name__':'ROOT_VERIFIED_RELOCATION_DATA_ONLY_POST','__file__':str(script)}
exec(compile(raw,str(script),'exec'),module)
for row in module['BINDINGS'].values(): assert module['bind'](row['path'])==row
guard_raw=module['GUARD'].read_bytes()
assert hashlib.sha256(guard_raw).hexdigest()==module['BINDINGS']['guard']['sha256']
guard={'__name__':'ROOT_VERIFIED_ORIGINAL_DATA_ONLY_POST','__file__':str(module['GUARD'])}
exec(compile(guard_raw,str(module['GUARD']),'exec'),guard)
config=json.loads(module['CONFIG'].read_bytes())
source,dest=module['SOURCE'],module['DEST']
if source.exists():
 assert module['metadata'](source)==module['ORIGINAL']
 physical='ORIGINAL_PATH_STILL_PRESENT'
else:
 mapping_path=module['OWNED']/'exact-original-path-to-new-physical-archive.json'
 assert mapping_path.is_file() and not mapping_path.is_symlink()
 mapping=json.loads(mapping_path.read_bytes())
 assert mapping['schema']=='EXACT_ONE_HISTORICAL_COMPRESSED_ARCHIVE_PHYSICAL_ALIAS'
 assert mapping['original']==module['ORIGINAL']
 assert mapping['original_index_binding']==module['BINDINGS']['index']
 assert mapping['original_index_unchanged'] is True
 actual=module['metadata'](dest)
 assert actual==mapping['new_physical']
 for key in ['bytes','sha256','mode','uid','gid','mtime_ns','nlink']: assert actual[key]==module['ORIGINAL'][key]
 config=module['alias_config'](config,source,dest)
 physical='EXACT_VERIFIED_NEW_ARCHIVE_ALIAS_ORIGINAL_PATH_ABSENT'
result=guard['protected'](config)
print(json.dumps({'status':'ROOT_INDEPENDENT_ALL_OUTCOME_DATA_POST_PASS','physical':physical,'protected':result,'native_execution':'NOT_RUN'}))
