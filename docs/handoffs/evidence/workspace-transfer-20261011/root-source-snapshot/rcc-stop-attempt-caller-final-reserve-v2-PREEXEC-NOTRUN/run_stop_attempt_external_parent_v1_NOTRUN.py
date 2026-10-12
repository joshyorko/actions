"""Distinct ROOT parent: external before/alwayspost enclose a finite inner call."""
import argparse
import json
import sys
import time
from pathlib import Path

sys.dont_write_bytecode=True
import stop_attempt_caller_contract_v1_NOTRUN as contract

def main():
    p=argparse.ArgumentParser()
    for key in ('caller-config-sha256','release','release-sha256'):p.add_argument('--'+key,required=True)
    args=p.parse_args();cfg,release=contract.admit(args,'external_parent');root=Path(cfg['root_once'])
    contract.need(not root.exists() and not root.is_symlink(),'STOP_PARENT_FRESH_ONCE_ROOT')
    contract.os.umask(0o077);root.mkdir(mode=0o700,exist_ok=False);contract.directory(root)
    contract.durable(root/'consumed-distinct-ROOT-release.json',{'release_binding':release,'caller_config_sha256':args.caller_config_sha256,'scope':'PURE_STOP_ATTEMPT_ONLY_NO_NATIVE'})
    argv=['timeout','--signal=TERM','--kill-after=10s','900s',contract.CACHED,
          cfg['implementation_bindings']['inner_caller']['path'],'--caller-config-sha256',args.caller_config_sha256,
          '--release',args.release,'--release-sha256',args.release_sha256]
    outcomes={};failure=None;started=time.monotonic();inner=None
    try:
        before=contract.capture(root,'external-before',contract.guard_argv(cfg),135);outcomes['before']=before
        contract.need(before.get('returncode')==0,'STOP_PARENT_BEFORE_FAILED');contract.admit(args,'external_parent')
        primary=contract.capture(root,'external-primary',argv,930);outcomes['primary']=primary
        contract.need(primary.get('returncode')==0,'STOP_PARENT_INNER_FAILED_OR_TIMEOUT')
        innerpath=root/'OWNERFINAL-original-stop-attempt-inner-four-phases.json';contract.physical(innerpath,0o400);inner=json.loads(innerpath.read_bytes())
        contract.need(inner.get('status')=='PASS_FOUR_PURE_PHASES_PENDING_INDEPENDENT_ORIGINALS' and inner.get('source')==cfg['source']
                      and inner.get('tree')==cfg['tree'] and inner.get('phase_order')==cfg['phase_order'],'STOP_PARENT_ORIGINAL_INNER_SCOPE')
        for name in cfg['phase_order']:contract.census(cfg,name)
    except BaseException as error:
        failure={'exception_class':type(error).__name__}
        contract.durable(root/'original-parent-primary-failure.private.json',{'exception_class':type(error).__name__,'private_error_text':str(error)})
    finally:
        try:
            post=contract.capture(root,'external-always-post',contract.guard_argv(cfg),135);outcomes['post']=post
            contract.need(post.get('returncode')==0,'STOP_PARENT_EXTERNAL_ALWAYSPOST_FAILED');contract.admit(args,'external_parent')
        except BaseException as error:
            if failure is None:failure={'post_exception_class':type(error).__name__}
            contract.durable(root/'original-parent-post-failure.private.json',{'exception_class':type(error).__name__,'private_error_text':str(error)})
    result={'schema':1,'status':'PASS_STOP_ATTEMPT_SOURCE_CONTROLS_PENDING_INDEPENDENT_ORIGINALS' if failure is None else 'FAIL_OR_HOLD_NO_RETRY',
            'source':cfg['source'],'tree':cfg['tree'],'outcomes':outcomes,'failure':failure,'release_binding':release,
            'inner_original_binding':contract.binding(root/'OWNERFINAL-original-stop-attempt-inner-four-phases.json') if inner else None,
            'elapsed_seconds':time.monotonic()-started,'native':'NOT_RUN','memory_profile_adoption':'NONE'}
    contract.durable(root/'OWNERFINAL-original-stop-attempt-external-parent.json',result,0o400)
    print(json.dumps({'status':result['status'],'native':'NOT_RUN'}))
    return 0 if failure is None else 1

if __name__=='__main__':raise SystemExit(main())
