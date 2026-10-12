from pathlib import Path
import hashlib,json,os
O=Path(__file__).parent;OLD=Path('/workspace/engineering/rcc-compatibility-owned-cache-runner-successor-preparation');PREV=Path('/workspace/engineering/rcc-current-e4ff-cache-mode-private-v8-proposal')
def write(name,raw):
 p=O/name;fd=os.open(p,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
 with os.fdopen(fd,'wb') as s:s.write(raw)
write('owned_cache_policy_v8.py',(PREV/'owned_cache_policy_v2.py').read_bytes())
write('fixture_records_v8.py',(PREV/'fixture_records_v3.py').read_bytes())
old=(OLD/'actual_transport_v7.py').read_text();new=old.replace('from owned_cache_policy_v1 import','from owned_cache_policy_v8 import').replace('from fixture_records_v2 import','from fixture_records_v8 import').replace("SOURCE = 'e4ff080375a8422bb656e52d218f198521dda078'","SOURCE = '396925cb3d6527af1768b7f5333f9653c005fc55'").replace("TREE = '973ff38f49a17a896e4d90f829a72e2ea0ea15e8'","TREE = '84f850f0d4e08b21afcd8220413ce94322370acf'")
assert old!=new;write('actual_transport_v8.py',new.encode())
controls=(PREV/'test_private_mode_source_v8.py').read_text().replace("'owned_cache_policy_v2'","'owned_cache_policy_v8'").replace("'fixture_records_v3'","'fixture_records_v8'").replace("SOURCE = 'e4ff080375a8422bb656e52d218f198521dda078'","SOURCE = '396925cb3d6527af1768b7f5333f9653c005fc55'").replace("TREE = '973ff38f49a17a896e4d90f829a72e2ea0ea15e8'","TREE = '84f850f0d4e08b21afcd8220413ce94322370acf'").replace("str(BASE/'proposed_test_source_staging_rcc_consumer.py')","'/workspace/engineering/pr308/action_server/tests/action_server_tests/test_source_staging_rcc_consumer.py'")
write('test_private_mode_source_current396925_v8.py',controls.encode())
print('PRIVATE_SOURCE_ONLY_NO_CONSTRUCTOR_CONFIG_ROOT_ACTUAL_OR_PRODUCT_MUTATION')
