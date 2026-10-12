"""Pure runner admission controls; contains no process launch or network code.

Future source/fixture configuration and raw-record adapters remain unbound.
Synthetic control success is not an actual compatibility qualification.
"""
import hashlib
import json
import math
import re
from decimal import Decimal
from xml.etree import ElementTree

SELECTORS = (
    'tests/action_server_tests/test_source_staging_rcc_consumer.py::test_published_artifact_details_preserves_one_rcc_identity_pair',
    'tests/action_server_tests/test_source_staging_rcc_consumer.py::test_staged_package_executes_in_managed_rcc_runtime',
)
CASE_NAMES = tuple(s.split('::')[1] for s in SELECTORS)
VERSION_ORDER = ('control3', 'released5', 'candidate7276')
EXACT_BUDGET = (600, 10, 645, 660, 10)
OPERATIONAL_STOP_BYTES = int(Decimal('2.35') * (1024**3))
HARD_ADMISSION_BYTES = int(Decimal('2.4') * (1024**3))
FIRST_COLD_FREE_BYTES = int(Decimal('3.6') * (1024**3))
WORKSPACE_FREE_BYTES = 1_200_000_000
SHA256 = re.compile('[0-9a-f]{64}\\Z')
GIT = re.compile('[0-9a-f]{40}\\Z')


class AdmissionFailure(ValueError):
    def __init__(self, code):
        super().__init__(code)
        self.code = code


def need(condition, code):
    if not condition:
        raise AdmissionFailure(code)


def exact_int(value):
    return type(value) is int


def valid_sha(value):
    return isinstance(value, str) and SHA256.fullmatch(value) is not None


def exact_keys(value, keys, code):
    need(type(value) is dict and set(value) == set(keys), code)


def parse_json_object(raw):
    def pairs(values):
        result = {}
        for key, value in values:
            need(key not in result, 'DUPLICATE_JSON_KEY')
            result[key] = value
        return result
    need(type(raw) is bytes and len(raw) <= 4_000_000, 'JSON_INPUT_BOUND')
    try:
        value = json.loads(raw, object_pairs_hook=pairs)
    except AdmissionFailure:
        raise
    except (UnicodeError, ValueError, TypeError):
        raise AdmissionFailure('MALFORMED_JSON') from None
    need(type(value) is dict, 'JSON_OBJECT_REQUIRED')
    return value


def validate_budget(values):
    need(type(values) in (tuple, list) and len(values) == 5, 'BUDGET_SHAPE')
    need(all(exact_int(v) and v > 0 for v in values), 'BUDGET_VALUE')
    need(tuple(values) == EXACT_BUDGET, 'BUDGET_CHANGED')
    need(values[2] == values[0] + 4 * values[1] + 5, 'HELPER_PARENT_BUDGET')


def validate_selectors(selectors):
    need(type(selectors) in (tuple, list) and tuple(selectors) == SELECTORS, 'SELECTOR_SET')


def validate_junit(raw):
    need(type(raw) is bytes and len(raw) <= 1_000_000, 'JUNIT_BOUND')
    need(b'<!DOCTYPE' not in raw and b'<!ENTITY' not in raw, 'JUNIT_DECLARATION')
    try:
        root = ElementTree.fromstring(raw)
    except (ElementTree.ParseError, ValueError):
        raise AdmissionFailure('JUNIT_PARSE') from None
    need(root.tag in ('testsuite', 'testsuites'), 'JUNIT_ROOT')
    suites = [root] if root.tag == 'testsuite' else list(root)
    need(len(suites) == 1 and suites[0].tag == 'testsuite', 'JUNIT_SUITE_COUNT')
    suite = suites[0]
    for key, expected in [('tests', '2'), ('failures', '0'), ('errors', '0'), ('skipped', '0')]:
        need(suite.get(key) == expected, 'JUNIT_COUNTER_' + key.upper())
    cases = list(suite)
    need(len(cases) == 2 and all(c.tag == 'testcase' for c in cases), 'JUNIT_CASE_COUNT')
    need(sorted(c.get('name', '') for c in cases) == sorted(CASE_NAMES), 'JUNIT_CASE_NAMES')
    need(all(c.get('classname', '').endswith('test_source_staging_rcc_consumer') for c in cases), 'JUNIT_CLASSNAME')
    need(all(not any(e.tag in ('skipped', 'failure', 'error') for e in c) for c in cases), 'JUNIT_OUTCOME')
    return {'tests': 2, 'passed': 2, 'skipped': 0, 'failures': 0, 'errors': 0}


def validate_source(record, expected):
    exact_keys(record, ('source_commit', 'source_tree', 'control_commit', 'control_tree', 'execution_kind'), 'SOURCE_RECORD_KEYS')
    for key in ('source_commit', 'source_tree', 'control_commit', 'control_tree'):
        need(isinstance(record[key], str) and GIT.fullmatch(record[key]) is not None, 'GIT_IDENTITY_' + key.upper())
        need(record[key] == expected[key], 'SOURCE_BINDING_' + key.upper())
    need(record['execution_kind'] == expected['execution_kind'] == 'isolated_external_two_case_qualification', 'EXECUTION_KIND')
    # External runner SHA256 is a distinct config field, never a legacy Git field.
    need(valid_sha(expected['runner_sha256']), 'RUNNER_CONTENT_IDENTITY')


def validate_binary(record, expected):
    keys = ('label', 'version', 'source', 'platform', 'sha256', 'acquisition_owner_sha256', 'acquisition_review_sha256', 'approved_copy_sha256')
    exact_keys(record, keys, 'BINARY_RECORD_KEYS')
    need(record['label'] in VERSION_ORDER, 'BINARY_LABEL')
    for key in keys:
        need(record[key] == expected[key], 'BINARY_BINDING_' + key.upper())
    need(record['platform'] == 'linux_amd64', 'BINARY_PLATFORM')
    need(GIT.fullmatch(record['source']) is not None, 'BINARY_SOURCE_GIT')
    for key in keys[4:]:
        need(valid_sha(record[key]), 'BINARY_DIGEST_' + key.upper())
    need(record['version'] in ('v18.19.3', 'v18.19.5', 'v18.19.6'), 'BINARY_VERSION')


def validate_lease(receipt, artifact_digest):
    # Actual raw-record adapters must bind their complete original bytes/schema.
    # These are the existing adapter's identity requirements plus terminal outcome.
    need(type(receipt) is dict, 'LEASE_OBJECT')
    need(receipt.get('artifactDigest') == artifact_digest, 'LEASE_ARTIFACT')
    need(type(receipt.get('verification')) is dict and receipt['verification'].get('valid') is True, 'LEASE_VERIFICATION')
    need(type(receipt.get('leaseId')) is str and bool(receipt['leaseId']), 'LEASE_IDENTITY')
    need(receipt.get('status') == 'completed', 'LEASE_STATUS')
    need(exact_int(receipt.get('exitCode')) and receipt['exitCode'] == 0, 'LEASE_EXIT')


def select_owned_pytest(captures, supervisor, argv_sha256, cwd):
    need(type(captures) is list, 'OWNERSHIP_CAPTURE')
    need(type(supervisor) is tuple and len(supervisor) == 2, 'SUPERVISOR_IDENTITY')
    need(exact_int(supervisor[0]) and supervisor[0] > 0, 'SUPERVISOR_PID')
    need(type(supervisor[1]) in (int, float) and type(supervisor[1]) is not bool and math.isfinite(supervisor[1]) and supervisor[1] > 0, 'SUPERVISOR_TIME')
    matches = []
    for row in captures:
        exact_keys(row, ('pid', 'create_time', 'parent_pid', 'argv_sha256', 'cwd', 'live', 'zombie'), 'CAPTURE_KEYS')
        need(exact_int(row['pid']) and row['pid'] > 0 and exact_int(row['parent_pid']), 'CAPTURE_PID')
        need(type(row['create_time']) in (int, float) and type(row['create_time']) is not bool and math.isfinite(row['create_time']) and row['create_time'] > 0, 'CAPTURE_TIME')
        need(type(row['live']) is bool and type(row['zombie']) is bool, 'CAPTURE_STATE')
        if row['parent_pid'] == supervisor[0] and row['argv_sha256'] == argv_sha256 and row['cwd'] == cwd:
            need(row['pid'] != supervisor[0] and row['live'] and not row['zombie'], 'PYTEST_OWNER_STATE')
            matches.append((row['pid'], row['create_time']))
    need(len(matches) == 1, 'PYTEST_OWNER_UNIQUE')
    return matches[0]


def authorize_signal(captured, current):
    need(type(captured) is tuple and captured == current, 'OWNED_PID_REUSED_OR_CHANGED')
    return 'SIGNAL_ONLY_MATCHED_PYTEST_CHILD_NO_WAIT_NO_SUPERVISOR_KILL'


def validate_sampler(marker):
    exact_keys(marker, ('stage', 'sample_count', 'maximum_observed_bytes', 'workspace_minimum_observed_bytes', 'threshold_triggered', 'inspection_error', 'sampler_cancelled', 'sampler_alive', 'peak_is_universal', 'kernel_quota'), 'SAMPLER_KEYS')
    need(marker['stage'] == 'final', 'SAMPLER_FINAL')
    for key in ('sample_count', 'maximum_observed_bytes', 'workspace_minimum_observed_bytes'):
        need(exact_int(marker[key]) and marker[key] >= 0, 'SAMPLER_COUNTER')
    need(marker['sample_count'] > 0, 'SAMPLER_NO_OBSERVATIONS')
    need(marker['sampler_cancelled'] is True and marker['sampler_alive'] is False, 'SAMPLER_NOT_JOINED')
    need(marker['inspection_error'] is False, 'SAMPLER_INSPECTION_ERROR')
    need(marker['threshold_triggered'] is False, 'SAMPLER_THRESHOLD')
    need(marker['maximum_observed_bytes'] < OPERATIONAL_STOP_BYTES, 'SAMPLER_OPERATIONAL_BOUND')
    need(marker['maximum_observed_bytes'] < HARD_ADMISSION_BYTES, 'SAMPLER_HARD_OBSERVED_BOUND')
    need(marker['workspace_minimum_observed_bytes'] >= WORKSPACE_FREE_BYTES, 'SAMPLER_WORKSPACE_FLOOR')
    need(marker['peak_is_universal'] is False and marker['kernel_quota'] is False, 'SAMPLER_SCOPE_OVERCLAIM')


def combine_outcomes(primary, cleanup):
    # Keep primary/cleanup fixed category values distinct; never normalize a FAIL.
    exact_keys(primary, ('code', 'status'), 'PRIMARY_KEYS')
    exact_keys(cleanup, ('code', 'status'), 'CLEANUP_KEYS')
    allowed_primary = {'COMMAND_COMPLETE', 'COMMAND_FAILED', 'COMMAND_TIMEOUT', 'CAPACITY_THRESHOLD', 'CAPTURE_INSPECTION_FAILED', 'ADMISSION_FAILED'}
    allowed_cleanup = {'CLEAN_NO_DESCENDANTS', 'REAPED_EXITED_DESCENDANTS', 'FORCED_OR_UNEXPECTED_DESCENDANTS', 'CLEANUP_FAILED', 'CLEANUP_UNAVAILABLE'}
    need(primary['code'] in allowed_primary and primary['status'] in ('PASS', 'FAIL'), 'PRIMARY_CATEGORY')
    need(cleanup['code'] in allowed_cleanup and cleanup['status'] in ('PASS', 'FAIL'), 'CLEANUP_CATEGORY')
    need((primary['status'] == 'PASS') == (primary['code'] == 'COMMAND_COMPLETE'), 'PRIMARY_STATUS_CODE')
    clean = cleanup['code'] in ('CLEAN_NO_DESCENDANTS', 'REAPED_EXITED_DESCENDANTS')
    need((cleanup['status'] == 'PASS') == clean, 'CLEANUP_STATUS_CODE')
    return {'status': 'PASS' if primary['status'] == cleanup['status'] == 'PASS' else 'FAIL', 'primary': dict(primary), 'cleanup': dict(cleanup)}


def next_version(label, preceding):
    need(label in VERSION_ORDER, 'VERSION_SEQUENCE_LABEL')
    index = VERSION_ORDER.index(label)
    need(type(preceding) is list and len(preceding) == index, 'VERSION_SEQUENCE_COUNT')
    need(all(row == {'label': VERSION_ORDER[i], 'status': 'PASS', 'tests': 2, 'skipped': 0, 'errors': 0} for i, row in enumerate(preceding)), 'VERSION_SEQUENCE_PREDECESSOR')
    return label
