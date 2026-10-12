import copy
import importlib.util
import json
from pathlib import Path

import pytest

O=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('controlled_current_qualified_constructor',O/'build_qualified_current8d49_config_v8_FINAL.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


def documents():
    review=json.loads(Path(module.FULL_REVIEW['path']).read_bytes())
    light=json.loads(Path(module.LIGHT_REVIEW['path']).read_bytes())
    inner=json.loads(Path(review['original_configured_FULL_terminal']['path']).read_bytes())
    original=json.loads(Path(review['original_ROOT_owner_binding']['path']).read_bytes())
    supplement=json.loads(Path(review['named_readonly_post_env_supplement']['path']).read_bytes())
    return inner,light,review,original,supplement


@pytest.mark.parametrize('poison,category',[
    ('inner_source','CURRENT_ORIGINAL_INNER_FULL_PASS'),
    ('inner_tree','CURRENT_ORIGINAL_INNER_FULL_PASS'),
    ('inner_status','CURRENT_ORIGINAL_INNER_FULL_PASS'),
    ('inner_bool_return','CURRENT_ORIGINAL_INNER_FULL_PASS'),
    ('inner_failed_post','CURRENT_ORIGINAL_INNER_FULL_PASS'),
    ('light_old_source','CURRENT_SOURCE_LIGHT_QUALIFICATION'),
    ('full_old_source','CURRENT_SOURCE_FULL_INDEPENDENT_QUALIFICATION'),
    ('full_old_count','CURRENT_SOURCE_FULL_INDEPENDENT_QUALIFICATION'),
    ('full_bool_count','CURRENT_SOURCE_FULL_INDEPENDENT_QUALIFICATION'),
    ('full_false_PASS','CURRENT_SOURCE_FULL_INDEPENDENT_QUALIFICATION'),
    ('root_relabelled_PASS','ORIGINAL_ROOT_POST_FAILURE_PRESERVED'),
    ('root_original_failure_omitted','ORIGINAL_ROOT_POST_FAILURE_PRESERVED'),
    ('supplement_wrong_terminal','SEPARATE_READONLY_POST_SUPPLEMENT_REQUIRED'),
    ('supplement_bad_status','SEPARATE_READONLY_POST_SUPPLEMENT_REQUIRED'),
    ('supplement_failed','SEPARATE_READONLY_POST_SUPPLEMENT_REQUIRED'),
])
def test_original_inner_pass_and_retained_root_failure_separate_supplement(poison,category):
    docs=documents();module.qualification_documents(*docs)
    docs=copy.deepcopy(docs);inner,light,full,root,supplement=docs
    if poison=='inner_source':inner['source']='0'*40
    elif poison=='inner_tree':inner['tree']='0'*40
    elif poison=='inner_status':inner['status']='FAIL'
    elif poison=='inner_bool_return':inner['primary']=False
    elif poison=='inner_failed_post':inner['post']=1
    elif poison=='light_old_source':light['source']['commit']='0'*40
    elif poison=='full_old_source':full['source']='0'*40
    elif poison=='full_old_count':full['complete_typed_source']=1423
    elif poison=='full_bool_count':full['actual_gate_results']['configured_primary']=False
    elif poison=='full_false_PASS':full['actual_gate_results']['pytest_PASS']=1427
    elif poison=='root_relabelled_PASS':root['status']='PASS'
    elif poison=='root_original_failure_omitted':root['independent_ROOT_post']=0
    elif poison=='supplement_wrong_terminal':supplement['original_FULL_terminal']['sha256']='0'*64
    elif poison=='supplement_bad_status':supplement['status']='NOT_RUN'
    else:supplement['returncode']=1
    action=[]
    with pytest.raises(module.need.__globals__['AdmissionFailure']) as error:
        module.qualification_documents(*docs)
        action.append('UNREACHED_NATIVE')
    assert error.value.code==category
    assert action==[]
