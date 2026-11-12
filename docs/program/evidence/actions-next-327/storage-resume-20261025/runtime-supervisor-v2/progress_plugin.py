"""Incremental pytest outcomes only; never serialize exception/report payloads."""
import hashlib
import json
import os
import time
from collections import Counter


def safe_nodeid(value):
    # Parametrized node IDs may contain synthetic or real credential values.
    head, marker, parameters = str(value).partition("[")
    if marker:
        return head + "[parameters-sha256:" + hashlib.sha256(parameters.encode()).hexdigest()[:20] + "]"
    return head


class Progress:
    def __init__(self, path):
        self.path = path
        self.counts = Counter()
        self.stream = None

    def emit(self, value):
        if self.stream is None:
            self.stream = open(self.path, "a", encoding="utf-8")
        self.stream.write(json.dumps(value, sort_keys=True) + "\n")
        self.stream.flush()
        os.fsync(self.stream.fileno())

    def pytest_sessionstart(self, session):
        self.emit({"event": "session_start", "time": time.time()})

    def pytest_runtest_logreport(self, report):
        outcome = report.outcome
        if getattr(report, "wasxfail", None):
            outcome = "xfailed" if outcome == "skipped" else "xpassed"
        self.counts[report.when + ":" + outcome] += 1
        self.emit({"event": "report", "nodeid": safe_nodeid(report.nodeid),
                   "phase": report.when, "outcome": outcome,
                   "duration": report.duration})

    def pytest_collectreport(self, report):
        if report.failed:
            self.counts["collection:failed"] += 1
            self.emit({"event": "report", "nodeid": safe_nodeid(report.nodeid),
                       "phase": "collection", "outcome": "failed", "duration": 0})

    def pytest_sessionfinish(self, session, exitstatus):
        self.emit({"event": "session_finish", "exitstatus": int(exitstatus),
                   "counts": dict(self.counts), "time": time.time()})
        self.stream.close()
        self.stream = None
