from pathlib import Path
import json,hashlib
p=Path('/workspace/actions-cloud/receipts/pr305-runner')
def rec(f):
 f=Path(f);return {'path':str(f),'sha256':hashlib.sha256(f.read_bytes()).hexdigest()}
a=json.loads((p/'immutable-runner-proposal-v3.json').read_text())
a['supersedes_without_overwrite']={'reason':'Current3ec/8ed/checkpointccfb/collectedsourcehashd84 pins and sourceproof schema; readonly emittedselector discovery/dependency readiness; preflight metadata/freshsuffix3 only. Actualworker/admission/helper/budgets unchanged.','runner':rec(p/'canvas-native-public-runner-v3.py'),'controls':rec(p/'test_runner_admission_v3.py'),'proposal':rec(p/'immutable-runner-proposal-v3.json'),'actual_failure':rec(p/'actual-v3-failed-checkpoint.json'),'failure_independent_review':rec('/workspace/engineering/pr305-v3-independent-runner-review/independent-actual-v3-failure-review.json'),'earlier_predecessors':a['supersedes_without_overwrite']}
a['runner']=rec(p/'canvas-native-public-runner-v4.py');a['controls']=rec(p/'test_runner_admission_v4.py')
a['gateway']['exact_argv'][-1]=a['gateway']['exact_argv'][-1].replace('canvas-native-public-runner-v3.py','canvas-native-public-runner-v4.py')
a['gateway']['discovery_command_seconds']=30;a['gateway']['discovery_helper_cleanup_seconds']=5
a['gateway']['meaning']+=' List-only preflight30scommand+existing5shelpercleanup is inside unchanged660souter; no increase to600command/645parent/660outer. Worst-case combination may be curtailed by outer660; no600overall claim.'
a['one_attempt_root']=str(p/'actual-3ec9d0acbe30ad94d02e4c24fef2587127964495-3')
a['source']={'head':'3ec9d0acbe30ad94d02e4c24fef2587127964495','tree':'8ed17c0c2ed48a3ad4fe89994bab572d028e59ca','ordered_parents':['066eb3e2bc997d0f84f2f539b08b85ccfa808a46','1c7585fe8bb3cb9476c3997570bd3f04466f2bbc'],'selector_fix':'066eb3e2bc997d0f84f2f539b08b85ccfa808a46','preserved_actual_predecessor_harness':'14c1c1965314b192c4118c3281f5539d29f0aa6f','producer_entries':268,'selected_test_entries':5,'source_checkpoint':rec('/workspace/actions-cloud/receipts/pr305-selector-fix/frozen-current-union-source-checkpoint.json'),'source_independent_review':rec('/workspace/engineering/pr305-selector-independent-source-review/independent-frozen-source-review.json')}
a.pop('source_mutated_after14c',None);a['source_mutated_after3ec']=False

a['native']['policy']='Original92498/tree80e5/1192 layout remains originalproducer. Current3ec all268+5 Gitbody/mode equality verified separately, not newnativeproducer. Fresh1192entryownedcopy/fullbefore-after parity; no build/wrapperrepeat. Later302union needs independentproducer admission.'
a['driver']['reuse']='Actualpr305/frontend/node_modules must already exist andresolveexactly to measuredpreparedpr310tree beforelist/consumer. Retain correct ignoredpreparedlink from priorV3. Missing/wronglink is readinessHOLD; no install/replacement. Originalexecute idempotentlinkcheck retained, but preflightrequireslinkalreadycorrect. No npm/coldregistryclaim.'
a['ownership']['collection']='V3exactonepytestnode/file/functionglobals unchanged; sourcehashpin d84 for3ec. OnlyCANVAS_OWNED_RUNNER installed/restored onactualitem.module; noaliases/product/assertion/expectationmutation.'
a['discovery_preflight']={'source_sha256':'d84f5e54dafb29e9beda15673769110952f165aee61c0deb5a04ee920515abcf','selector':r'^\s*host-harness\.spec\.ts official bridge renders a real Runtime Action result$','meaning':'Parseverifiedsourcebytebuffer AST actualemittedgrep. NodeCLI --list via unchanged282owner selects1intendedspec/testentry/no globalerrors. No browser/start/sourcebuild/Runtime/provisioning. Actualworkercommand unchanged; actualJSON1passed0skip/retry and5toolRun gate unchanged.','list_scope':'Playwrightlist unexecuted entry hasstatusskipped/results[]/expected0/skipped1. This is discovery inventory, neither executedskip norPASS/zero-skipacceptance.','receipts':[rec(p/('v4-driver-discovery-'+label+'.json')) for label in ['GREEN','oldzero','broadtwo','wrongfixture']],'readiness':'actualnode_modules.is_dir and.resolve==measuredpreparedtree; validbaseline/absent/wrongcontrols'}
a['preparation']['log']=rec(p/'immutable-runner-v4-final-controls.log')
a['preparation']['command']='activatedRCC gateway action_server PoetryRuffformat/check; pytest -c pyproject.toml /workspace/actions-cloud/receipts/pr305-runner/test_runner_admission_v4.py -q -n0 --tb=short; python canvas-native-public-runner-v4.py without execute flag'
a['preparation']['result']='56service-freeactual-validator/helper/realcollection/lockeddriver controlsPASS/0skip; RuffPASS;1192/268+5+onecase listpreflightPASS; V4consumerNOTRUN'
a['preparation']['cause_and_fix']='Source14c V3 zeroPlaywrightcases/no browser retained. Reviewed source066/currenttargetunion3ec selectorfix; V4currentpins/actualemittedselector+executeddeps readiness only, no consumerbehavior rewrite.'
a['preparation']['real_collection_evidence']=rec(p/'v4-real-collection-controls.json');a['preparation']['ast_scope_proof']=rec(p/'v4-ast-scope-proof.json')
a['preparation']['negative_controls']+=['actualsource-extracted lockeddriver:correctone; oldzero realCalledProcessError/NoTestsFound; broadtwo/wrongfixture rawJSON rejected','actualfrontenddependencylink validbaseline/absent/wrong target refuses']
a['preparation']['prior_v4_qualification']=rec(p/'immutable-runner-v4-controls.log')
a['preparation']['prior_v3_preparation_causes']='All V3 logs preserved. InitialV4 54controlPASS retained; thenreviewer-required actualCLI dependencybinding/2controls, final56PASS.'
doc='''Canonical file proposed: docs/skills/repository-operations.md, following its implemented Playwright discovery paragraph. Source3ec remains frozen; this external qualification proposes the exact backed addition for integration.

> Bind dependency measurements to the path the command actually executes. Before
> Playwright discovery or browser execution, require the frontend's `node_modules`
> to resolve to the measured prepared tree. A missing or different ignored link is
> a readiness failure; measuring another dependency directory does not qualify the
> executed CLI. Preserve the prepared tree and record whether its existing link is
> retained, rather than silently installing or replacing dependencies.
>
> Keep list-only discovery inventory separate from executed-case admission. The
> locked Playwright driver's `--list` report contains an unexecuted entry with empty
> results and skipped status/counters. Admit discovery by the exact intended spec
> and test-entry count with no global errors; continue requiring one actually
> passing case with zero skips/retries and the existing five tool Runs at execution.
> Record the discovery deadline and its helper cleanup within the unchanged outer
> gateway budget. Retain the current harness identity independently of the native
> artifact's original producer, with all producer inputs and full artifact bytes
> checked before and after the actual attempt.

Documentation improvement:
- Canonical file changed or proposed: source3ec guide integrates source066/accepted reviewer lessons; runner-only exact followup proposed here, no source mutation.
- Durable learning: actual executed CLI dependency binding; discovery skipped inventory differs from executed admission; finite preflight remains inside unchanged outer deadline.
- Evidence: measured actual prepared link, locked driver onecase/oldzero/broadtwo/wrongfixture receipts,56controls including absent/wronglink,1192/273 preflight, preserved V3 NoTestsFound failure/8bf independent review. No V4 consumer executed.
- Stale ambiguity removed: prepared hash authenticates any existing frontend tree; list skipped inventory proves execution; preflight expands deadlines; later harness becomes native producer.
- Remaining uncertainty: actual current3ec/native92498 browser/publicCore/fiveToolRuns/sharedcache/strictcleanup NOT_RUN; no later302/fullCore/coldregistry/realartifact/productionhost/ChatGPT/OAuth release/wholeepic proof.

Upstream disposition: none. Local test/controller collection and dependency binding, not a verified upstream defect.
'''
(p/'canonical-runner-v4-proposed-delta.md').write_text(doc)
a['documentation_improvement']={'Canonical_file_changed_or_proposed':'docs/skills/repository-operations.md changed066/current3ec; exactrunner-onlyfollowup proposed','Durable_learning':'actualCLIdependency binding/list-only skipped inventory insideunchangedbounds','Evidence':'reviewed3ec/preservedV3failure;56controls+actualNode list+1192/273preflight;V4actualNOTRUN','Stale_guidance_removed':'preparedhashbindsanyfrontend; listskip=execution; preflightextendsbudget; nativeproducerrelabelling','Remaining_uncertainty':'current3ec/native92498 actualbrowser/publicCore/fiveRuns/sharedcachecleanup pending; later302/fullCore/coldregistry/productartifact/OAuth/wholeepic unqualified','exact_delta':rec(p/'canonical-runner-v4-proposed-delta.md'),'source_integrated_delta':rec('/workspace/actions-cloud/receipts/pr305-selector-fix/canonical-current-union.patch')}
(p/'immutable-runner-proposal-v4.json').write_text(json.dumps(a,indent=2,sort_keys=True)+'\n')
for name in ['canvas-native-public-runner-v4.py','test_runner_admission_v4.py','immutable-runner-proposal-v4.json','canonical-runner-v4-proposed-delta.md','v4-ast-scope-proof.json','v4-real-collection-controls.json']+['v4-driver-discovery-'+v+'.json' for v in ['GREEN','oldzero','broadtwo','wrongfixture']]:
 f=p/name;f.chmod(0o444)
 if name in ['canvas-native-public-runner-v4.py','test_runner_admission_v4.py','immutable-runner-proposal-v4.json','canonical-runner-v4-proposed-delta.md']:print(json.dumps(rec(f)))
