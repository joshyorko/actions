"""Four literal synthetic phases; current source guard before every phase/post."""
import argparse
import json
import sys
import time
from pathlib import Path

sys.dont_write_bytecode=True
import stop_attempt_caller_contract_v1_NOTRUN as contract

def main():
    started=time.monotonic();primary_deadline=started+765
    p=argparse.ArgumentParser()
    for key in ('caller-config-sha256','release','release-sha256'):p.add_argument('--'+key,required=True)
    args=p.parse_args();cfg,release=contract.admit(args,'inner_caller');root=Path(cfg['root_once']);contract.directory(root)
    marker=json.loads((root/'consumed-distinct-ROOT-release.json').read_bytes())
    contract.need(marker=={'release_binding':release,'caller_config_sha256':args.caller_config_sha256,'scope':'PURE_STOP_ATTEMPT_ONLY_NO_NATIVE'},'STOP_INNER_PARENT_MARKER')
    outcomes={};failure=None;censuses={}
    try:
        for name in cfg['phase_order']:
            contract.admit(args,'inner_caller')
            guarded=contract.capture(root,'inner-guard-'+name,contract.guard_argv(cfg),135,primary_deadline=primary_deadline)
            outcomes['guard-'+name]=guarded
            contract.need(guarded.get('returncode')==0,'STOP_INNER_PHASE_GUARD_FAILED')
            phase=cfg['phase_expectations'][name];out=Path(phase['output'])
            contract.need(out.parent==root and not out.exists() and not out.is_symlink(),'STOP_INNER_FRESH_PHASE_OUTPUT')
            # capture creates the original phase helper's exclusive700 output.
            observed=contract.capture(root,name,contract.phase_argv(cfg,args.release_sha256,name),135,primary_deadline=primary_deadline)
            outcomes[name]=observed
            contract.need(observed.get('returncode')==0,'STOP_INNER_PHASE_FAILED_OR_WRONG_RED')
            censuses[name]=contract.census(cfg,name)
            contract.admit(args,'inner_caller')
    except BaseException as error:
        failure={'exception_class':type(error).__name__}
        contract.durable(root/'original-inner-primary-failure.private.json',{'exception_class':type(error).__name__,'private_error_text':str(error)})
    finally:
        try:
            post=contract.capture(root,'inner-always-post',contract.guard_argv(cfg),135);outcomes['always-post']=post
            contract.need(post.get('returncode')==0,'STOP_INNER_ALWAYSPOST_FAILED');contract.admit(args,'inner_caller')
        except BaseException as error:
            if failure is None:failure={'post_exception_class':type(error).__name__}
            contract.durable(root/'original-inner-post-failure.private.json',{'exception_class':type(error).__name__,'private_error_text':str(error)})
    result={'schema':1,'status':'PASS_FOUR_PURE_PHASES_PENDING_INDEPENDENT_ORIGINALS' if failure is None else 'FAIL_OR_HOLD_NO_RETRY',
            'source':cfg['source'],'tree':cfg['tree'],'phase_order':cfg['phase_order'],'outcomes':outcomes,'census_bindings':censuses,
            'failure':failure,'elapsed_seconds':time.monotonic()-started,'native':'NOT_RUN','memory_profile_adoption':'NONE'}
    contract.durable(root/'OWNERFINAL-original-stop-attempt-inner-four-phases.json',result,0o400)
    return 0 if failure is None else 1

if __name__=='__main__':raise SystemExit(main())
