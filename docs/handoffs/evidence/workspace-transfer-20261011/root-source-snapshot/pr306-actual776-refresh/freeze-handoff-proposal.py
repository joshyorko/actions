from pathlib import Path
import difflib,hashlib,json
out=Path('/workspace/engineering/pr306-actual776-refresh');root=Path('/workspace/engineering/pr306');path='action_server/tests/action_server_tests/test_cli_mcp_resource_history.py';old=(root/path).read_text()
# Use the exact GREEN predicate, with existing typed signature and normal formatting.
probe=(out/'test_handoff_probe.py').read_text();start=probe.index('def full_handoff(client):');end=probe.index('\n\ndef test_b_publication',start);helper=probe[start:end].replace('def full_handoff(client):','def _resource_handoff_is_published(client: httpx.Client) -> bool:')+'\n\n\n'
new=old.replace('def _read_text(client: httpx.Client, uri: str) -> str:',helper+'def _read_text(client: httpx.Client, uri: str) -> str:')
a='''                template = transition["candidate_kind"] == "template"
                wait_for_condition(
                    lambda transition=transition, template=template: _route_is_listed(
                        client, transition["candidate_uri"], template=template
                    ),'''
b='''                wait_for_condition(
                    lambda: _resource_handoff_is_published(client),'''
assert new.count(a)>=1;new=new.replace(a,b,1)
patch=''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='a/'+path,tofile='b/'+path));(out/'proposed-handoff-test-only.patch').write_text(patch)
g='docs/skills/repository-operations.md';text=(root/g).read_text();addition='''\nFor watched MCP ownership handoffs between independently refreshed packages, a new
candidate route being listed does not prove the previous package has relinquished
its declarations. An assembled-catalog control can publish the new template while
the old direct route remains listed and still validly serves the old owner. Wait
for all intended candidate declarations and the absence of every old declaration
before asserting historical-owner rejection. Keep callback nonexecution and
unrelated-URI success checks. The two resource-list RPCs are separate observations;
this barrier is not an atomic catalog snapshot, nor proof of a hosted failure's
actual update order. Preserve deadlines and the original failed execution tuple.\n'''
patch=''.join(difflib.unified_diff(text.splitlines(True),(text.rstrip()+'\n'+addition).splitlines(True),fromfile='a/'+g,tofile='b/'+g));(out/'proposed-handoff-canonical.patch').write_text(patch)
bind=lambda p:{'path':str(p),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
r={'status':'DETERMINISTIC_SERVICE_FREE_ORDERING_PROOF_PROPOSAL_ONLY','current_head':'d3c4cee69ea715779bb28ada0d8fea2ccb72e0d7','current_tree':'90c7a268f2d3ebbf8419d8ba669e5ebfd020769c','actual_tested_original_checkout':'11484f93750b51cafc052b46030cfcbd89f2ee18','test_blob_unchanged':'534e51afbc75b4d3ce473dee37d7ac00d52dbc92','RED':'legacy B-only wait TRUE while A-v2 direct owner valid; expected false assertion FAILED1','GREEN':'combined B-presence plus all old A-declaration absence FALSE before A removal, TRUE after A removal; strict historical conflict blocks every old concrete URI without callback; other B URIs/B-safe/A-control success; PASS1','transport':'existing actual _CustomFastAPI/_ActionRoutes/SQLite catalog + TestClient, synthetic callback only, same transition and route definitions, no native/frozen/runtime process or watcher','warning_scope':'standalone owned probe outside package conftest produced3199 existing deprecation warnings in each bounded invocation','proposed_source_scope':'one existing CLI helper plus first handoff admission wait predicate only; preserves per-transition30s/50ms waits and all assertions/callbacks/restart/deadlines. Regression to integrate after independent design GO using existing catalog fixture/actual catalog responses rather than new production implementation.','separate_RPC_limit':'resources/list and resources/templates/list are not atomic; fixture removes A claims monotonically and does not reintroduce until later restart','hosted_cause':'UNKNOWN: deterministic witness proves insufficient wait condition, not actual hosted scheduling or timestamp cause','native_input_disposition':'proposal changes one of five selected tests and requires new source selector binding; no native old tuple carry','documentation':{'file_proposed':g,'durable_learning':'Candidate presence alone is not cross-package ownership handoff completion; require old declaration absence plus all candidate presence, retain semantic assertions and separate-RPC limitation','evidence':'actual assembled ordering control RED1/GREEN1','stale_ambiguity_removed':'No inference that new route visibility proves previous owner relinquishment','remaining_uncertainty':'actual Linux update order and native V2 observer observations unavailable'},'Upstream_disposition':'none','source_mutation':False,'evidence':[bind(out/n) for n in ['test_handoff_probe.py','handoff-legacy-RED.log','handoff-legacy-exit.json','handoff-full-GREEN.log','proposed-handoff-test-only.patch','proposed-handoff-canonical.patch','safe-original-linux-handoff-hypothesis.json','safe-original-linux-log-census.json']]}
(out/'frozen-handoff-ordering-proof-proposal.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(bind(out/'frozen-handoff-ordering-proof-proposal.json')))
