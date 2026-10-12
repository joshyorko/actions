import hashlib,importlib.util,json
from pathlib import Path
review=Path('/workspace/engineering/windows-next-observation-independent-review/independent-v2-design-review.json');assert hashlib.sha256(review.read_bytes()).hexdigest()=='95f44464acd56e278a87890e0c5f24da9b38cbfb044f925f48bbf1c2221355e3'
binding=json.loads(review.read_text())['independent_grounding'];source=Path('tests/action_server_tests/native_startup_diagnostics.py').resolve();spec=importlib.util.spec_from_file_location('reviewed_diagnostic_parser',source);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
probe=module.DeliveredObservations(began=0,clock=lambda:1.0)
for mark in binding['original299_numeric_marks']:
 probe.line('stderr',f"####  Progress: {mark['step']:02d}/15  v18.19.3  {mark['since_previous_seconds']:.3f}s private suffix ignored")
report=probe.summary();assert report['progress']['interval_sum_seconds']==binding['original299_sum_seconds']==89.259
assert len(report['progress']['marks'])==16 and report['observation_loss'] is False
assert 'private' not in json.dumps(report)
r={'status':'SERVICE_FREE_CURRENT_PARSER_MATCHES_AUTHENTICATED_HISTORICAL_NUMERIC_MARKS','parser_source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'immutable_original299_review_sha256':hashlib.sha256(review.read_bytes()).hexdigest(),'expected_sum':89.259,'measured_numeric_parser_sum':report['progress']['interval_sum_seconds'],'marks':16,'actual306_native_timing':'UNAVAILABLE_NOT_EXECUTED; historical input fixture only, never relabeled','no_raw_suffix_retained':True}
out=Path('/workspace/engineering/pr306-windows-v2-source/historical-interval-parser-control.json');assert not out.exists();out.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
