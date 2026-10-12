import dataclasses, hashlib, importlib.util, json, os, sys, tempfile
from pathlib import Path
import pytest
from actions.server.deployments import source_staging as stager
from actions.server.deployments import source_read
ROOT=Path('/workspace/engineering/pr282')
assert Path(stager.__file__).resolve()==ROOT/'action_server/src/actions/server/deployments/source_staging.py'
assert Path(sys.prefix).resolve()==ROOT/'action_server/.venv'
spec=importlib.util.spec_from_file_location('owned_staging_test',ROOT/'action_server/tests/contract_tests/test_source_staging.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
real_fstat=os.fstat
real_observation=source_read._observation
def sha(data):return hashlib.sha256(data).hexdigest()
def stats(value):return {key:getattr(value,key) for key in ('st_dev','st_ino','st_size','st_mtime_ns','st_ctime_ns')}
results=[]
for kind,count in [('unchanged_original',16),('original_after_read_constant_timestamps',1),('before_read_constant_timestamps',1)]:
 for index in range(count):
  with tempfile.TemporaryDirectory(prefix='owned-',dir='/workspace/engineering/pr282-staged-read-diagnosis') as temporary:
   root=Path(temporary);destination=root/'staging';destination.mkdir(mode=0o700)
   root_fd=os.open(root,os.O_RDONLY|os.O_DIRECTORY);destination_fd=os.open(destination,os.O_RDONLY|os.O_DIRECTORY)
   records=[]
   class InstrumentedPatch(pytest.MonkeyPatch):
    def setattr(self,target,name,value,raising=True):
     if target is stager.os and name=='read' and getattr(value,'__name__',None)=='mutate_staged_read':
      original=value;cells=dict(zip(original.__code__.co_freevars,original.__closure__))
      def recording_read(fd,size):
       before=real_fstat(fd);path=destination/'input';targeted=path.exists() and (before.st_dev,before.st_ino)==(path.stat().st_dev,path.stat().st_ino)
       if targeted and kind=='before_read_constant_timestamps' and not cells['mutated'].cell_contents:
        path.write_bytes(b'modified');cells['mutated'].cell_contents=True
       chunk=original(fd,size)
       after=real_fstat(fd)
       if targeted:
        records.append({'returned_size':len(chunk),'returned_sha256':sha(chunk),'actual_metadata_before':stats(before),'actual_metadata_after':stats(after),'mutation_flag':cells['mutated'].cell_contents,'metadata_equal':stats(before)==stats(after)})
       return chunk
      return super().setattr(target,name,recording_read,raising)
     return super().setattr(target,name,value,raising)
   patch=InstrumentedPatch()
   if kind!='unchanged_original':
    patch.setattr(source_read,'_observation',lambda s:dataclasses.replace(real_observation(s),mtime_ns=0,ctime_ns=0))
   try:
    try:
     module.test_staged_bytes_are_rechecked_and_mutation_cleans_owned_tree(root,root_fd,(destination,destination_fd),patch)
     outcome='PASS';error=None
    except BaseException as exc:
     outcome='FAIL';error={'class':type(exc).__name__,'did_not_raise':str(exc).startswith('DID NOT RAISE'),'assertion':str(exc) if str(exc).startswith('DID NOT RAISE') else 'OTHER'}
    remaining=list(destination.iterdir());final=sha((destination/'input').read_bytes()) if (destination/'input').exists() else None
    results.append({'kind':kind,'index':index,'test_outcome':outcome,'error':error,'stage_reads':records,'remaining_entry_count':len(remaining),'final_bytes_sha256':final,'timestamps_model':'actual' if kind=='unchanged_original' else 'explicit_test_observation_shim_constant_zero'})
   finally:
    patch.undo();os.close(destination_fd);os.close(root_fd)
receipt={'schema':'original-staging-node-owned-source-probe/v1','original_callable_assertions_unchanged':True,'production_source_unchanged':True,'source_origin_and_own_prefix_verified':True,'fixture_bytes':{'original':sha(b'original'),'modified':sha(b'modified')},'results':results}
Path('/workspace/engineering/pr282-staged-read-diagnosis/measurement.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({'bounded_cases':len(results),'counts':{kind:{outcome:sum(r['kind']==kind and r['test_outcome']==outcome for r in results) for outcome in ('PASS','FAIL')} for kind in sorted({r['kind'] for r in results})}}))
