"""Preserve connector-decoded job text and report only bounded CI evidence."""
import hashlib
import json
import re
import sys
from pathlib import Path

job_id = int(sys.argv[1])
root = Path(__file__).resolve().parent
connector = root / f"job-{job_id}-decoded-connector-private.json"
result = json.loads(connector.read_bytes())
strings = []

def collect(value, path):
    if isinstance(value, str):
        if len(value) > 1000:
            strings.append((path, value))
    elif isinstance(value, dict):
        for key, child in value.items():
            collect(child, path + [key])
    elif isinstance(value, list):
        for index, child in enumerate(value):
            collect(child, path + [index])

collect(result, [])
assert strings, "No complete decoded log text in connector result"
field, text = max(strings, key=lambda entry: len(entry[1]))
assert "Set up job" in text or "Current runner version" in text
raw = text.encode("utf-8")
log_path = root / f"job-{job_id}-decoded-private.log"
assert not log_path.exists(), "Never overwrite retained decoded logs"
log_path.write_bytes(raw)
log_path.chmod(0o600)
connector.chmod(0o600)
lines = text.splitlines()
summary = [line for line in lines if re.search(r"\b\d+ (?:failed|passed|skipped).*\bin \d", line)]
sha_candidates = []
for i, line in enumerate(lines):
    if "log -1" in line and "format" in line:
        for following in lines[i + 1:i + 4]:
            match = re.search(r"Z\s+[\"']?([0-9a-f]{40})[\"']?\s*$", following)
            if match:
                sha_candidates.append(match.group(1))
merge_lines = [line for line in lines if "HEAD is now at" in line]
names = [
    "test_provider_startup_failure_uses_bounded_kill_fallback",
    "test_regression_handles_reported_child_distinct_from_original_popen",
    "test_startup_regression_reports_failed_cleanup_and_disposes_original_child",
    "test_fixture_child_capture_rejects_unknown_or_changed_identity",
    "test_fixture_child_stop_check_rejects_reused_identity",
    "test_async_zero_admits_cancel_before_held_worker_runs",
    "test_server_async_process_poll_with_cancel",
]
named = {
    name: [line for line in lines if name in line and re.search(r"\b(?:PASSED|FAILED|SKIPPED)\b", line)]
    for name in names
}
receipt = {
    "schema": 1,
    "job": job_id,
    "retrieval": "One connector fetch of completed job; exact UTF-8 encoding of received decoded text, not original HTTP/archive bytes",
    "connector_json": str(connector),
    "connector_json_sha256": hashlib.sha256(connector.read_bytes()).hexdigest(),
    "decoded_field": field,
    "decoded_log": str(log_path),
    "decoded_log_bytes": len(raw),
    "decoded_log_sha256": hashlib.sha256(raw).hexdigest(),
    "leading_utf8_bom": raw.startswith(b"\xef\xbb\xbf"),
    "crlf_count": raw.count(b"\r\n"),
    "lf_count": raw.count(b"\n"),
    "suite_summaries": summary,
    "producer_sha_candidates": sha_candidates,
    "producer_checkout_lines": merge_lines,
    "named_test_events": named,
    "native_baseline_attempts": 0,
}
path = root / f"job-{job_id}-log-extraction-receipt.json"
path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
print(json.dumps({"job": job_id, "sha256": receipt["decoded_log_sha256"], "bytes": len(raw), "bom": receipt["leading_utf8_bom"], "crlf": receipt["crlf_count"], "summaries": summary, "producer": sha_candidates, "named_results": {name: ["FAILED" if "FAILED" in event else "PASSED" if "PASSED" in event else "SKIPPED" for event in events] for name, events in named.items()}}, indent=2))
