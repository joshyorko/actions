import json, hashlib, subprocess
from pathlib import Path
from types import SimpleNamespace
head = "fe1bdee3d5014d39a763d088535c29d65b38315d"
source = subprocess.check_output(["git", "-C", "/workspace/actions-pr308", "show", head + ":action_server/scripts/verify_dakota_rcc_acceptance.py"])
ns = {"__name__": "immutable_review"}
exec(compile(source, head, "exec"), ns)
E, I, R, W = (ns[n] for n in ("OwnedCleanupEvidence", "OwnedIdentity", "OwnedCensusRow", "OwnedReapEvent"))
root, child = I(1, 1.0), I(2, 10.0)
root_only = E(1, "subreaper_source_observation_only", root, True, True, 0, True, (), (R(root, "absent", 4.0, None, 1, None),), (), True, (), (), None, None, None)
controls = []
def check(name, passed):
    assert passed, name
    controls.append({"name": name, "pass": bool(passed)})
check("valid_root_only_complete", E.from_dict(root_only.to_dict()).census_reap_complete)
with_child = root_only._replace(census=root_only.census + (R(child, "absent", 4.0, None, 2, None),))
check("absent_child_without_birth_witness_incomplete", not E.from_dict(with_child.to_dict()).census_reap_complete)
for pid in (2, 999):
    forged = with_child._replace(reap_events=(W(pid, 0, 3.0, child),))
    try:
        E.from_dict(forged.to_dict())
        rejected = False
    except ValueError:
        rejected = True
    check("reap_birth_rejected_pid_" + str(pid), rejected)
    check("parent_transport_unavailable_pid_" + str(pid), ns["_transport_cleanup_evidence"]({"cleanup_evidence": forged.to_dict()}).observation_errors == ("ValueError",))
    check("raw_forged_child_completion_false_pid_" + str(pid), not forged.census_reap_complete)
for pid in (None, 999, True):
    forged = root_only._replace(census=(root_only.census[0]._replace(observed_pid=pid),))
    try:
        E.from_dict(forged.to_dict())
        rejected = False
    except ValueError:
        rejected = True
    check("known_row_pid_rejected_" + str(pid), rejected)
    check("known_row_parent_unavailable_" + str(pid), not ns["_transport_cleanup_evidence"]({"cleanup_evidence": forged.to_dict()}).census_reap_complete)
check("raw_wait_pid_does_not_prove_birth", not E.from_dict(root_only._replace(reap_events=(W(1, 0, 3.0, None),)).to_dict()).census_reap_complete)
class Missing(Exception):
    pass
obs = ns["_OwnedCleanupObserver"]()
obs.root = root
obs.root_capture_verified = True
obs.root_wait_reaped = True
obs.root_wait_returncode = 0
obs.enumeration_succeeded = True
obs.terminal_echild = True
obs.rows[root] = R(root, "unknown", 1.0, None, 1, None)
def vanished():
    raise Missing()
obs.observe_final(lambda pid: SimpleNamespace(create_time=lambda: 1.0, status=vanished), missing_error=Missing, observed_at=4.0)
parsed = ns["_observer_cleanup_evidence"](obs)
check("status_race_preserves_census", parsed.census == (R(root, "absent", 4.0, None, 1, None),))
check("status_race_no_metadata_error", parsed.observation_errors == ())
check("status_race_does_not_invent_reap", parsed.reap_events == ())
check("unavailable_facts_never_complete", not E.unavailable().census_reap_complete)
check("failed_enumeration_never_complete", not E.from_dict(root_only._replace(enumeration_succeeded=False, enumeration_errors=("OSError",)).to_dict()).census_reap_complete)
result = {"head": head, "source_sha256": hashlib.sha256(source).hexdigest(), "scope": "immutable stdlib models; no native, signals or provider launch", "controls": controls, "passed": len(controls)}
Path(__file__).with_name("immutable-model.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps({"head": head, "passed": len(controls)}))
