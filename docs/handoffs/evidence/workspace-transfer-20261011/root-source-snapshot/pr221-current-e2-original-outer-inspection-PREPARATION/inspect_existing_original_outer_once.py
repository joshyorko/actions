"""Root-released existing-file outer inspection only; no transfer or extraction."""
import ast
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
import time
import traceback
import zipfile

HERE=Path(__file__).resolve().parent
OWNER=HERE/'OWNERFINAL-current-e2-existing-original-outer-inspection-PREEXECUTION.json'
RELEASE=Path('/workspace/engineering/root-current-e2-one-existing-original-outer-inspection-release.json')
OUTPUT=Path('/workspace/engineering/root-current-e2-one-existing-original-outer-inspection-owned')
INPUTS=HERE/'private-original-existing-file-and-failed-transfer-input-bindings.json'
EXECUTOR=Path('/workspace/engineering/pr221-current-e2-producer-reconciliation/acquire_current_e2_aggregate_once.py')
POLICY=EXECUTOR.parent/'frozen-current-e2-publisher-outer-archive-policy.json'
ZIP=Path('/tmp/actions-pr221-e2-aggregate-11708952448-one-owned/actions-runtime-dist-11708952448-original.zip')
INPUT_BINDING={'path': '/workspace/engineering/pr221-current-e2-original-outer-inspection-PREPARATION/private-original-existing-file-and-failed-transfer-input-bindings.json', 'bytes': 3149, 'sha256': '2c4dbc7d82e99e1538631084e1dbb5ed398c56d531e5ec1e5c761e817ad9a98f', 'mode': '0o400'}


def binding(path):
    p=Path(path);s=p.lstat();assert stat.S_ISREG(s.st_mode) and not p.is_symlink()
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return {'path':str(p),'bytes':s.st_size,'sha256':h.hexdigest(),'mode':oct(stat.S_IMODE(s.st_mode))}


def write(path,value):
    with path.open('x',encoding='utf-8')as f:
        os.chmod(path,0o600);f.write(json.dumps(value,indent=2,sort_keys=True)+'\n');f.flush();os.fsync(f.fileno())


def guard(rows):
    assert binding(INPUTS)==INPUT_BINDING
    for path,row in rows.items():assert binding(path)==row


def main():
    assert sys.flags.optimize==0 and not os.environ.get('PYTHONOPTIMIZE')
    assert sys.argv[1:]==['--root-execute-one-existing-original-outer-inspection',str(RELEASE)]
    assert binding(RELEASE)['mode']=='0o600'
    release=json.loads(RELEASE.read_bytes())
    assert release['schema']=='ROOT_ONE_CURRENT_E2_EXISTING_ORIGINAL_OUTER_INSPECTION'
    assert release['one_attempt']is True and release['no_transfer_retry']is True
    assert release['proposal_binding']==binding(OWNER) and release['wrapper_binding']==binding(Path(__file__).resolve())
    assert release['artifact_id']==11708952448 and type(release['artifact_id'])is int
    assert release['outer_seconds']==120 and release['TERM_kill_after_seconds']==10
    row=release['independent_preexec_binding'];assert binding(row['path'])==row
    review=json.loads(Path(row['path']).read_bytes())
    assert review['decision']=='GO_CURRENT_E2_ORIGINAL_OUTER_INSPECTION_PREEXECUTION'
    assert review['proposal_binding']==release['proposal_binding']
    assert not OUTPUT.exists();os.umask(0o077);OUTPUT.mkdir(mode=0o700)
    write(OUTPUT/'consumed-one-root-release.json',release)
    rows=json.loads(INPUTS.read_bytes());primary=None;result={'status':'NOT_STARTED','original_transfer':'FAIL_RETAINED','inner_consumer_native':'NOT_RUN'}
    try:
        guard(rows);deadline=time.monotonic()+110
        raw=EXECUTOR.read_bytes();assert hashlib.sha256(raw).hexdigest()==rows[str(EXECUTOR)]['sha256']
        tree=ast.parse(raw);names=['require','filenames','inspect_zip']
        nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name in names]
        assert [n.name for n in nodes]==names
        ns={'re':re,'stat':stat,'time':time,'hashlib':hashlib,'zipfile':zipfile}
        exec(compile(ast.Module(body=nodes,type_ignores=[]),str(EXECUTOR),'exec'),ns)
        policy=json.loads(POLICY.read_bytes())
        assert policy['source']=='e2c81adce7858d5a952991ba9a8b7f72e902038a'
        assert ZIP.stat().st_size<=policy['compressed_byte_ceiling']
        fd=os.open(ZIP,os.O_RDONLY)
        try:os.fsync(fd)
        finally:os.close(fd)
        inventory=ns['inspect_zip'](ZIP,policy,deadline)
        write(OUTPUT/'private-original-eight-member-outer-inventory.json',inventory)
        result.update(status='PASS_ORIGINAL_E2_OUTER_ONLY_PENDING_POSTGUARD',outer_members=len(inventory),distribution_files=7,manifest_records=7,whole_ZIP=rows[str(ZIP)],new_transfer='NOT_RUN',extraction='NOT_RUN',original_socket_BadFD='FAIL_RETAINED; not retroactively repaired')
    except BaseException as exc:
        primary=exc;result['status']='FAIL';result['primary_exception_type']=type(exc).__name__
        try:write(OUTPUT/'primary-failure.private.json',{'traceback':traceback.format_exc()})
        except BaseException as retain:
            if hasattr(primary,'add_note'):primary.add_note('Primary retention also failed: '+type(retain).__name__)
    finally:
        try:guard(rows);result['protected_post']='PASS'
        except BaseException as secondary:
            result['status']='FAIL';result['protected_post']='FAIL'
            try:write(OUTPUT/'secondary-postguard-failure.private.json',{'traceback':traceback.format_exc()})
            except BaseException:pass
            if primary is None:primary=secondary
            elif hasattr(primary,'add_note'):primary.add_note('Postguard also failed: '+type(secondary).__name__)
        if primary is None:result['status']='PASS_ORIGINAL_E2_AGGREGATE_OUTER_DATA_ONLY'
        try:write(OUTPUT/'OWNERFINAL-one-existing-original-outer-inspection-result.json',result)
        except BaseException as retention:
            if primary is None:primary=retention
            elif hasattr(primary,'add_note'):primary.add_note('Final retention also failed: '+type(retention).__name__)
    if primary is not None:raise primary


if __name__=='__main__':main()
