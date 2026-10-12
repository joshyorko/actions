import dataclasses,hashlib,json,os,tempfile
from pathlib import Path
import pytest
from actions.server.deployments import source_staging as stager,source_read
original_observation=source_read._observation
real_read=os.read
cases=[]
for phase in ('none','before_read','after_read'):
 with tempfile.TemporaryDirectory(prefix='digest-owned-',dir='/workspace/engineering/pr282-staged-read-diagnosis') as temporary:
  root=Path(temporary);(root/'input').write_bytes(b'original');dst=root/'staging';dst.mkdir(mode=0o700)
  source_fd=os.open(root,os.O_RDONLY|os.O_DIRECTORY);dst_fd=os.open(dst,os.O_RDONLY|os.O_DIRECTORY)
  patch=pytest.MonkeyPatch();patch.setattr(source_read,'_observation',lambda s:dataclasses.replace(original_observation(s),mtime_ns=0,ctime_ns=0));mutated=False;read_chunks=[]
  def inject(fd,size):
   global mutated
   opened=os.fstat(fd);path=dst/'input';targeted=path.exists() and (opened.st_dev,opened.st_ino)==(path.stat().st_dev,path.stat().st_ino)
   if targeted and not mutated and phase=='before_read':path.write_bytes(b'modified');mutated=True
   chunk=real_read(fd,size)
   if targeted:read_chunks.append(hashlib.sha256(chunk).hexdigest())
   if targeted and not mutated and phase=='after_read':path.write_bytes(b'modified');mutated=True
   return chunk
  patch.setattr(stager.os,'read',inject)
  try:
   try:
    inventory=stager.stage_selected_files(source_fd,dst_fd,['input'],protected_input_names=[])
    outcome='RETURNED';error=None;inventory_sha=inventory.inventory.entries[0].sha256
   except ValueError as exc:outcome='REJECTED';error=str(exc);inventory_sha=None
   actual_sha=hashlib.sha256((dst/'input').read_bytes()).hexdigest() if (dst/'input').exists() else None
   assert outcome==('REJECTED' if phase=='before_read' else 'RETURNED')
   if phase=='before_read':assert mutated and list(dst.iterdir())==[] and 'staged source bytes changed' in error
   if phase=='none':assert inventory_sha==actual_sha==hashlib.sha256(b'original').hexdigest()
   if phase=='after_read':assert mutated and inventory_sha==hashlib.sha256(b'original').hexdigest() and actual_sha==hashlib.sha256(b'modified').hexdigest()
   cases.append({'phase':phase,'outcome':outcome,'mutation_executed':mutated,'read_chunk_sha256':read_chunks,'inventory_sha256':inventory_sha,'actual_final_sha256':actual_sha,'error':error,'remaining_entries':len(list(dst.iterdir())),'timestamps_model':'explicit_test_observation_shim_constant_zero'})
  finally:patch.undo();os.close(source_fd);os.close(dst_fd)
Path('/workspace/engineering/pr282-staged-read-diagnosis/digest-boundary-control-receipt.json').write_text(json.dumps({'cases':cases,'all_expected_control_results':True,'production_code_unchanged':True,'after_read_concurrent_write_violates_exclusive_destination_writer_contract':True},indent=2)+'\n')
print('VALID_CONSTANT_TIMESTAMP_BASELINE_RETURNED; BEFORE_READ_SAME_SIZE_POISON_REJECTED_CLEAN; AFTER_READ_CONSTANT_METADATA_CONTROL_RETURNED_PRIOR_BYTES=VERIFIED')
