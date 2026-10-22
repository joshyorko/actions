"""Dedicated Linux browser applicability must precede imported fixture setup."""

import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def test_unsupported_invoice_browser_skips_before_filesystem_fixture(tmp_path):
    tests = Path(__file__).resolve().parents[1]
    probe = """
import sys,pytest
sys.path.insert(0,sys.argv[1])
from action_server_tests import test_invoice_canvas_mcp as invoices
invoices.pytestmark=pytest.mark.skipif(True,reason='owned unsupported-platform applicability control')
@pytest.fixture
def forbidden_store():
    raise AssertionError('filesystem fixture constructed before applicability')
invoices.store=forbidden_store
raise SystemExit(pytest.main([sys.argv[1]+'/action_server_tests/test_invoice_canvas_browser.py','-q','--junitxml='+sys.argv[2]]))
"""
    report = tmp_path / "selection.xml"
    result = subprocess.run(
        [sys.executable, "-I", "-c", probe, str(tests), str(report)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    cases = ET.parse(report).findall(".//testcase")
    assert len(cases) == 2 and all(case.find("skipped") is not None for case in cases)
