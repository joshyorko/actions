"""ROOT primary shim, imports synthetic controls only after complete admission."""
import importlib.util
import json
import os
from pathlib import Path
import sys
import unittest

sys.dont_write_bytecode=True
sys.path.insert(0,'/workspace/engineering/rcc-current8d49-cgroup-reader28-concrete-PREEXEC-NOTRUN')
from run_root_reader28_pure_once_NOTRUN import admission,parse_arguments,durable,read_bound,physical,need


def flatten(suite):
    for test in suite:
        if isinstance(test,unittest.TestSuite):
            yield from flatten(test)
        else:
            yield test


def main():
    args=parse_arguments();need(args.phase=='primary','READER28_PRIMARY_ONLY')
    cfg,_=admission(args,primary=True)
    root=Path(cfg['root_once']);physical_parent=root/'primary'
    need(root.is_dir() and not root.is_symlink() and physical_parent.is_dir() and not physical_parent.is_symlink(),'READER28_PARENT_OWNED')
    need(root.stat().st_uid==physical_parent.stat().st_uid==os.getuid()==1000 and root.stat().st_gid==physical_parent.stat().st_gid==os.getgid()==1000,'READER28_PRIVATE_PARENT_OWNER')
    need(root.stat().st_mode & 0o777==0o700 and physical_parent.stat().st_mode & 0o777==0o700,'READER28_PRIVATE_PARENT_MODE')
    read_bound(cfg['controls'])
    spec=importlib.util.spec_from_file_location('frozen_reader28_controls',cfg['controls']['path'])
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    suite=unittest.TestLoader().loadTestsFromModule(module)
    ids=[test.id() for test in flatten(suite)]
    need(ids==cfg['expected_method_ids'] and len(ids)==28 and len(set(ids))==28,'READER28_EXACT_COLLECTED_METHODS_BEFORE_RUN')
    class Result(unittest.TextTestResult):
        def __init__(self,*a,**k):
            super().__init__(*a,**k);self.success_ids=[]
        def addSuccess(self,test):
            self.success_ids.append(test.id());super().addSuccess(test)
    actual=unittest.TextTestRunner(stream=sys.stderr,verbosity=2,resultclass=Result).run(suite)
    need(not getattr(actual,'expectedFailures',[]) and not getattr(actual,'unexpectedSuccesses',[]),'READER28_NO_EXPECTED_FAILURE_MASK')
    counts={'ran':actual.testsRun,'passed':len(actual.success_ids),'failed':len(actual.failures),'errors':len(actual.errors),'skipped':len(actual.skipped)}
    passed=counts=={'ran':28,'passed':28,'failed':0,'errors':0,'skipped':0} and actual.success_ids==ids
    read_bound(cfg['controls'])
    for row in cfg['frozen_bindings']:read_bound(row)
    admission(args,primary=True)
    durable(physical_parent/'original-unittest-node-census.json',{'schema':1,'status':'PASS_28_SYNTHETIC_METHODS_NO_BACKEND_ADOPTION' if passed else 'FAIL_SYNTHETIC_CONTROLS_NO_RETRY',
            'counts':counts,'expected_ids':ids,'success_ids':actual.success_ids,
            'failure_ids':[test.id() for test,_ in actual.failures],'error_ids':[test.id() for test,_ in actual.errors],
            'skipped_ids':[test.id() for test,_ in actual.skipped],'subtest_scope':'28 unittest methods; subtest calls not relabelled as independent methods',
            'source':cfg['source'],'tree':cfg['tree'],'controls_binding':cfg['controls'],'native':'NOT_RUN',
            'backend_full_descriptor_walk':'NOT_TESTED_SEPARATE_CONTROLS_REQUIRED','policy_adoption':'NONE'})
    return 0 if passed else 1


if __name__=='__main__':
    raise SystemExit(main())
