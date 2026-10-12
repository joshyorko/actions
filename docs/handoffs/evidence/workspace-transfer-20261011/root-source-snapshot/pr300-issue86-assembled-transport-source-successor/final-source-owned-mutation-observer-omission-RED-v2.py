from contextlib import contextmanager
from pathlib import Path
import hashlib,json,pytest,subprocess
O=Path("/workspace/engineering/pr300-issue86-assembled-transport-source-successor")
R=Path("/workspace/engineering/pr300")
assert subprocess.check_output(["git","rev-parse","HEAD"],cwd=R,text=True).strip()=="74beef4d220c3a1e8f983cecd42b9bb84ac75e79"
SOURCE_SHA="712e55b646160311ad00170ac39f574aa7fdce2a2597d82ead49b38966d4a554"
assert hashlib.sha256((R/"action_server/tests/action_server_tests/run_outputs/test_transport.py").read_bytes()).hexdigest()==SOURCE_SHA
class OmitObserver:
    def __init__(self):self.controls=[]
    def pytest_runtest_call(self,item):
        self.module=item.module;self.runtime=item.funcargs["runtime"];self.original=self.module._unchanged_transport_state;self.before=None;self.changed=None
        @contextmanager
        def disabled(runtime):
            self.before=self.module._transport_state(runtime.datadir,runtime.store[0].db_path)
            try:yield
            finally:self.changed=self.module._transport_state(runtime.datadir,runtime.store[0].db_path)
        self.module._unchanged_transport_state=disabled
    def pytest_runtest_teardown(self,item):
        if hasattr(self,"original"):
            self.module._unchanged_transport_state=self.original
            after=self.module._transport_state(self.runtime.datadir,self.runtime.store[0].db_path)
            kind=item.callspec.params["change"]
            sql_changed=self.before[0]!=self.changed[0];fs_changed=self.before[1]!=self.changed[1]
            assert (sql_changed,fs_changed)==((True,False) if kind=="sql-row" else (False,True))
            assert after==self.before
            self.controls.append(dict(case=kind,actual_SQL_changed=sql_changed,actual_owned_FS_changed=fs_changed,actual_complete_state_restored=True))
plugin=OmitObserver()
code=pytest.main(["-n","0","-p","no:cacheprovider","-p","no:robocorp_log_pytest","--junitxml="+str(O/"final-source-owned-mutation-observer-omission-RED-v2-junit.xml"),"--basetemp="+str(O/"final-source-owned-mutation-observer-omission-RED-v2-temp"),"tests/action_server_tests/run_outputs/test_transport.py::test_transport_state_observer_detects_owned_mutation_and_restores","-q"],plugins=[plugin])
assert code==1 and len(plugin.controls)==2
(O/"final-source-owned-mutation-observer-omission-RED-v2-proof.json").write_text(json.dumps(dict(head="74beef4d220c3a1e8f983cecd42b9bb84ac75e79",source_SHA=SOURCE_SHA,actual_pytest_code=int(code),expected_omission_failures=2,actual_owned_mutations_and_measured_restoration=plugin.controls,production_no_mutations=True),indent=2)+"\n")
assert hashlib.sha256((R/"action_server/tests/action_server_tests/run_outputs/test_transport.py").read_bytes()).hexdigest()==SOURCE_SHA
