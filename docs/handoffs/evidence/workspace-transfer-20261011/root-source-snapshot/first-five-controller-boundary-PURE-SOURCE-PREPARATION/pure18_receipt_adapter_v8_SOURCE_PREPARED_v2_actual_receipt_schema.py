"""Data-only proposed typed adapter. Originals retain their narrower raw status."""
from pathlib import Path
import math


def adapt(census, raw_binding, actual_independent, source_owner, source_config):
    expected = source_config['expected_nodeids']
    assert len(expected) == len(set(expected)) == 18
    assert raw_binding['path'] == str(Path(source_config['owned_root']) / 'original-18-complete-machine-census.json')
    assert raw_binding['mode'] == '0o600'
    assert type(raw_binding['bytes']) is int and raw_binding['bytes'] > 0
    assert len(raw_binding['sha256']) == 64 and all(c in '0123456789abcdef' for c in raw_binding['sha256'])
    assert actual_independent['decision'] == 'GO_FIRST_FIVE_V8_ACTUAL_PURE18_ONLY'
    assert actual_independent['original_census_binding'] == raw_binding
    assert actual_independent['prepared_source_owner'] == source_owner
    assert actual_independent['actual_binding'] == raw_binding
    result = actual_independent['original_actual_result']
    assert result['child_beforePASS_postPASS'] is True and result['master0_external_before0_child0_external_alwayspost0'] is True
    assert result['exact18_uniqueIDs_selected_outcome_stdio_match'] is True
    assert result['actual_driver_compile_of_checked_buffer634_path_origin_verified'] is True
    assert result['five_stdlib_origins_before_after_same_measured_own_prefix'] is True
    assert result['original_census_status'] == 'PASS_PURE_CONTROLS_ONLY' and result['raw_status_not_rewritten'] is True
    assert type(result['tests_run']) is int and result['tests_run'] == 18
    assert all(type(result[k]) is int and result[k] == 0 for k in ('failure_count', 'error_count', 'skip_count'))
    assert census['schema'] == 'ORIGINAL_UNITTEST_18_COMPLETE_MACHINE_CENSUS_V1'
    assert census['status'] == 'PASS_PURE_CONTROLS_ONLY'
    assert type(census['tests_run']) is int and census['tests_run'] == 18
    for key in ('failure_count', 'error_count', 'skip_count'):
        assert type(census[key]) is int and census[key] == 0
    ids = census['selected_nodeids']
    assert len(ids) == len(set(ids)) == 18 and set(ids) == set(expected)
    rows = census['outcomes']
    assert len(rows) == 18 and len({row['nodeid'] for row in rows}) == 18
    assert {row['nodeid'] for row in rows} == set(expected)
    assert all(row['status'] == 'PASSED' for row in rows)
    assert census['source_assertions_unchanged'] is True
    assert census['native_or_storage_qualification'] is False
    assert type(census['elapsed_seconds']) in (int, float) and math.isfinite(census['elapsed_seconds']) and 0 <= census['elapsed_seconds'] <= 120
    assert Path(census['actual_python']).resolve() == Path(source_config['cached_python']['path']).resolve()
    assert census['actual_prefix'] == source_config['cached_prefix']
    before = census['stdlib_origins_before']; after = census['stdlib_origins_after']
    assert before == after and len(before) == 5 and len({row['module'] for row in before}) == 5
    assert {row['module'] for row in before} == set(source_config['stdlib_origin_bindings'])
    for row in before:
        expected_origin = source_config['stdlib_origin_bindings'][row['module']]
        assert row['path'] == expected_origin['path'] and row['sha256'] == expected_origin['sha256']
    driver = census['verified_driver_origin']; expected_driver = source_config['preservation_driver']
    assert driver['status'] == 'VERIFIED_BUFFER_SOURCE_MODULE'
    assert driver['path'] == expected_driver['path'] and driver['module_file'] == expected_driver['path'] and driver['sha256'] == expected_driver['sha256']
    assert driver['loader'] == 'compile_of_hash_checked_raw_buffer'
    return {'schema': 'ROOT_TYPED_V8_PURE18_DERIVED_ADMISSION_V1', 'status': 'PASS',
            'tests_run': 18, 'failure_count': 0, 'error_count': 0, 'skip_count': 0,
            'raw_status': census['status'], 'raw_census_binding': raw_binding,
            'raw_actual_independent': actual_independent,
            'prepared_source_owner': source_owner,
            'native_or_storage_qualification': False}
