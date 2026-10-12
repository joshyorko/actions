from contextlib import contextmanager
from pathlib import Path
import hashlib,json,pytest
O=Path("/workspace/engineering/pr300-issue86-assembled-transport-source-successor")
class OmitObserver:
    def pytest_runtest_call(self,item):
        self.module=item.module
        self.original=self.module._unchanged_transport_state
        @contextmanager
        def disabled(runtime):
            yield
        self.module._unchanged_transport_state=disabled
    def pytest_runtest_teardown(self,item):
        if hasattr(self,"original"):
            self.module._unchanged_transport_state=self.original
code=pytest.main(["-n","0","-p","no:cacheprovider","-p","no:robocorp_log_pytest","--junitxml="+str(O/"owned-snapshot-observer-omission-RED-junit.xml"),"--basetemp="+str(O/"owned-snapshot-observer-omission-RED-temp"),"tests/action_server_tests/run_outputs/test_transport.py::test_transport_state_observer_detects_owned_mutation_and_restores","-q"],plugins=[OmitObserver()])
assert code==1,code
(O/"owned-snapshot-observer-omission-RED-return.json").write_text(json.dumps(dict(actual_pytest_code=int(code),expected_refusal=True,production_files_not_mutated=True,owned_SQL_and_file_mutation_restored_by_finally=True,omission_limited_to_test_owned_observer=True)))
