"""Pure controls prepared only; do not import product or launch a native child."""
import importlib.util
from pathlib import Path
import pytest
spec=importlib.util.spec_from_file_location("memory_contract", Path(__file__).with_name("proposed_cgroup_memory_state_v1_NOTRUN.py"))
policy=importlib.util.module_from_spec(spec)
spec.loader.exec_module(policy)

def baseline():
    return {"identity": ("0::/", 1, 2), "max": 17179869184, "current": 10000000000,
            "events": {"oom": 6, "oom_kill": 3, "oom_group_kill": 0},
            "events_local": {"oom": 6, "oom_kill": 0, "oom_group_kill": 0}}

def test_valid_baseline_and_same_counters():
    state=policy.MemoryState(baseline())
    assert state.observe(baseline()) is None
    assert state.primary is None and state.samples == 1

@pytest.mark.parametrize("key,bad,category", [("max","max","MEMORY_FINITE_COUNTER"),("max",True,"MEMORY_FINITE_COUNTER"),("current",False,"MEMORY_FINITE_COUNTER"),("identity",("0::/",True,2),"MEMORY_IDENTITY")])
def test_malformed_before_rejected_after_valid_baseline(key,bad,category):
    assert policy.admit_before(baseline())
    value=baseline();value[key]=bad
    with pytest.raises(policy.MemoryAdmissionError,match=category): policy.admit_before(value)

def test_existing_high_oom_counts_do_not_attribute_current_attempt():
    state=policy.MemoryState(baseline());assert state.observe(baseline()) is None

def test_admission_fresh_headroom_is_separate_from_mount_space():
    assert policy.admit_before(baseline())
    value=baseline();value["current"]=value["max"]-policy.CGROUP_INITIAL_HEADROOM_BYTES+1
    with pytest.raises(policy.MemoryAdmissionError,match="MEMORY_INITIAL_HEADROOM"): policy.admit_before(value)

@pytest.mark.parametrize("table,key",[("events","oom"),("events","oom_kill"),("events_local","oom_kill"),("events_local","oom_group_kill")])
def test_new_oom_event_latches_failure(table,key):
    state=policy.MemoryState(baseline());assert state.observe(baseline()) is None
    value=baseline();value[table][key]+=1
    assert state.observe(value)["code"]=="MEMORY_OOM_COUNTER_INCREASE"
    assert state.observe(baseline())["code"]=="MEMORY_OOM_COUNTER_INCREASE"

@pytest.mark.parametrize("delta",[0,-1])
def test_reserve_equal_or_below_latches(delta):
    state=policy.MemoryState(baseline());assert state.observe(baseline()) is None
    value=baseline();value["current"]=value["max"]-(policy.CGROUP_RESERVE_BYTES+delta)
    assert state.observe(value)["code"]=="MEMORY_RESERVE_THRESHOLD"

@pytest.mark.parametrize("kind",["identity","max","decrease","unknown"])
def test_identity_reset_or_unknown_rejects_after_valid_baseline(kind):
    state=policy.MemoryState(baseline());assert state.observe(baseline()) is None
    value=baseline()
    if kind=="identity":value["identity"]=("0::/other",1,2)
    if kind=="max":value["max"]+=1
    if kind=="decrease":value["events"]["oom"]-=1
    if kind=="unknown":value=None
    assert state.observe(value)["status"]=="FAIL"
