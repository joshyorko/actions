"""Prepared exact original16 baseline/two known RED/new20 GREEN phase shim.

ROOT must first adopt a separately reviewed config/release. No native/profile or
real cgroup backend is imported/executed by this source-only synthetic control.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import stat
import sys
import traceback
import unittest
import hashlib

sys.dont_write_bytecode=True
BASE=Path('/workspace/engineering/rcc-current8d49-memory-stop-attempt-successor-SOURCE-NOTRUN')
CFG=BASE/'FROZEN-stop-attempt-composition-pure-control-config-NOTRUN.json'


def need(ok,code):
 if not ok:raise ValueError(code)


def read_bound(row):
 p=Path(row['path']);s=p.lstat();need(stat.S_ISREG(s.st_mode) and not p.is_symlink(),'STOP_PURE_REGULAR')
 raw=p.read_bytes();need(len(raw)==row['bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256'] and stat.S_IMODE(s.st_mode)==int(row['mode'],8),'STOP_PURE_BINDING')
 return raw


def physical(path,mode):
 p=Path(path);s=p.lstat();need(stat.S_ISREG(s.st_mode) and not p.is_symlink() and stat.S_IMODE(s.st_mode)==mode and s.st_uid==os.getuid()==1000 and s.st_gid==os.getgid()==1000,'STOP_PURE_PHYSICAL')


def load(row,name):
 read_bound(row);spec=importlib.util.spec_from_file_location(name,row['path']);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def flatten(suite):
 for test in suite:
  if isinstance(test,unittest.TestSuite):yield from flatten(test)
  else:yield test


def main():
 p=argparse.ArgumentParser()
 for name in ('config-sha256','release','release-sha256','phase'):p.add_argument('--'+name,required=True)
 a=p.parse_args();physical(CFG,0o400);raw=CFG.read_bytes();need(hashlib.sha256(raw).hexdigest()==a.config_sha256,'STOP_PURE_CONFIG_SHA');cfg=json.loads(raw)
 physical(a.release,0o600);grant=Path(a.release).read_bytes();need(hashlib.sha256(grant).hexdigest()==a.release_sha256,'STOP_PURE_ROOT_RELEASE_SHA');release=json.loads(grant)
 need(a.release==cfg['root_release_path'] and release['decision']=='ROOT_RELEASE_ONE_STOP_ATTEMPT_SOURCE_CONTROLS_ONLY' and release['config_sha256']==a.config_sha256 and release['helper_sha256']==cfg['helper']['sha256'] and release['source']==cfg['source'] and release['tree']==cfg['tree'] and release['serialized_no_other_heavy_or_storage_mutations'] is True,'STOP_PURE_DISTINCT_ROOT_RELEASE')
 review=json.loads(read_bound(release['independent_PREEXEC']))
 need(review['status']=='INDEPENDENT_STOP_ATTEMPT_COMPOSITION_PURE_PREEXECUTION_GO' and review['source']==cfg['source'] and review['tree']==cfg['tree'] and review['config_sha256']==a.config_sha256 and review['helper_sha256']==cfg['helper']['sha256'],'STOP_PURE_INDEPENDENT_CONCRETE_GO')
 need(not sys.flags.optimize and 'PYTHONOPTIMIZE' not in os.environ and 'PYTEST_ADDOPTS' not in os.environ,'STOP_PURE_NO_INHERITED_OVERRIDE')
 need(Path(sys.prefix).resolve()==Path(cfg['runtime_prefix']).resolve() and Path(sys.executable).resolve()==Path(cfg['runtime_python']).resolve(),'STOP_PURE_OWN_RUNTIME')
 for row in cfg['bindings']:read_bound(row)
 need(Path(__file__).resolve()==Path(cfg['helper']['path']).resolve(),'STOP_PURE_SELF_PATH');read_bound(cfg['helper'])
 need(a.phase in cfg['phases'],'STOP_PURE_KNOWN_PHASE');phase=cfg['phases'][a.phase]
 out=Path(phase['output']);root=Path(cfg['root_once']);need(out.parent==root and out.is_dir() and not out.is_symlink() and stat.S_IMODE(out.stat().st_mode)==0o700,'STOP_PURE_EXCLUSIVE_PARENT')
 need(not (out/'original-node-census.json').exists(),'STOP_PURE_FRESH_CENSUS')
 module=load(cfg['controls'],'frozen_stop_attempt_controls')
 if phase['overlay_role']=='original_held':
  module.m=load(cfg['original_overlay'],'known_original_held_memory_overlay')
 suite=unittest.TestSuite(module.CompositionControls(name) for name in phase['methods'])
 ids=[test.id() for test in flatten(suite)];need(ids==phase['expected_ids'],'STOP_PURE_EXACT_COLLECTED_METHODS')
 class Result(unittest.TextTestResult):
  def __init__(self,*v,**kw):super().__init__(*v,**kw);self.success_ids=[];self.semantic=[]
  def addSuccess(self,test):self.success_ids.append(test.id());super().addSuccess(test)
  def addFailure(self,test,error):
   typ,value,tb=error;frames=[]
   while tb:
    code=tb.tb_frame.f_code
    if Path(code.co_filename).resolve()==Path(cfg['controls']['path']).resolve():frames.append({'function':code.co_name,'line':tb.tb_lineno})
    tb=tb.tb_next
   self.semantic.append({'test':test.id(),'exception_class':typ.__name__,'control_frames':frames});super().addFailure(test,error)
 actual=unittest.TextTestRunner(stream=sys.stderr,verbosity=2,resultclass=Result,failfast=True).run(suite)
 counts={'ran':actual.testsRun,'passed':len(actual.success_ids),'failed':len(actual.failures),'errors':len(actual.errors),'skipped':len(actual.skipped)}
 admitted=counts==phase['expected_counts'] and not actual.expectedFailures and not actual.unexpectedSuccesses
 if phase['kind']=='RED':
  predicate=phase['predicate'];admitted=admitted and len(actual.semantic)==1 and actual.semantic[0]['exception_class']=='AssertionError' and actual.semantic[0]['test']==ids[0] and {'function':predicate['function'],'line':predicate['line']} in actual.semantic[0]['control_frames']
 else:admitted=admitted and actual.success_ids==ids
 for row in cfg['bindings']:read_bound(row)
 physical(CFG,0o400);need(hashlib.sha256(CFG.read_bytes()).hexdigest()==a.config_sha256,'STOP_PURE_POST_CONFIG');physical(a.release,0o600);need(hashlib.sha256(Path(a.release).read_bytes()).hexdigest()==a.release_sha256,'STOP_PURE_POST_RELEASE')
 record={'schema':1,'status':'EXPECTED_SOURCE_PHASE_ADMITTED' if admitted else 'FAIL_OR_WRONG_RED_STOP_NO_RETRY','phase':a.phase,'counts':counts,'expected_ids':ids,'success_ids':actual.success_ids,'semantic':actual.semantic,'native':'NOT_RUN','real_cgroup_signals':'NOT_RUN','source':cfg['source'],'tree':cfg['tree']}
 fd=os.open(out/'original-node-census.json',os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
 with os.fdopen(fd,'wb') as f:f.write((json.dumps(record,indent=2,sort_keys=True)+'\n').encode());f.flush();os.fsync(f.fileno())
 directory=os.open(out,os.O_RDONLY|os.O_DIRECTORY)
 try:os.fsync(directory)
 finally:os.close(directory)
 return 0 if admitted else 1


if __name__=='__main__':raise SystemExit(main())
