# Serialization and Robot authoring independent source review

Read-only review; no root edits, executions of Robot jobs, installs, or external writes. Reviewed immutable patches:

- serialization.patch SHA256 3f1320abe6efda402cfb3407e6bcc62264358317d587366b2be2f7509d25b6a1
- robot-authoring.patch SHA256 e0d96ed9911ebc766eb6e6cb1f6e63c2b7b51be491a4ecb4268a87a9421a42b8
- shared-wiring-PROPOSAL.patch SHA256 b8e1fa5ba2a64198a92ca0313798570432e0a839ab6ba3fb5c68554520931fe0

## Serialization disposition

Approved bounded change. Both generated helpers use the exact Core actions/_action.py conversion: when the result has model_dump, call model_dump(mode='json'). Existing strict JSON serialization, byte limits, private exclusive output creation and host schema validation remain in force. No stringification fallback is added. Delivery records eight focused passing tests across plain/logical helpers and model/mapping/unsupported/nonfinite results; initial fixture/helper-name failures remain retained. This reviewer inspected source and receipts, did not rerun tests. The trusted-artifact reproduction establishes the original failure, not installed qualification of the fix. Generated failure lifecycle was intentionally not reviewed.

## Robot authoring disposition

No blocker found in the isolated adapter/validator slice or proposed all-Package readiness loop. The request remains closed; no caller runtime paths/receipts are accepted. Runtime selection is explicit with no RCC-to-direct fallback. The adapter reloads retained admission and validation through the registry port. The validator checks source/plan, exact suite/task and pinned runtime, supervises bounded logs/XML with live checks, confirms process cleanup, rechecks source bytes/modes, and binds diagnostic bytes in the canonical receipt. Real Robot XML statistics/suite is correctly separated from executable suite selection.

The SQL proposal checks every referenced Package during activation with require_ready=True. Projection preserves unready evidence instead of overwriting it with a later ready Package. Python CompilationEvidence readiness remains required; Robot source-only evidence can be staged but cannot activate.

Mandatory root-owned integration dependency: the registry must issue validation through trusted host invocation, bind that issuance to the exact admission ticket and full Package reference/source/plan, retain receipt plus diagnostic preimages atomically, and verify them on reload. verify_robot_validation is a consistency verifier, NOT issuance authority. RobotAuthoringEvidence.ready alone only checks a nonempty receipt and status; never accept arbitrary constructed evidence through package_evidence. Replay must not grant authority; old source-only rows must remain readable and unready. Ensure live authorization is rechecked at retention and activation. No new schema or scheduler is implied.

Evidence inspected: robot-authoring-lane/RECEIPT.md, dedicated and shared test source, canonical verifier and process supervision source, shared wiring patch. Producer reports 44 dedicated passes including real direct dry-run, and 12 shared passes/2 explicitly unconfigured PostgreSQL skips. These are not independently rerun counts. Actual RCC validation stopped before publish on the disk guard; not executed, not approval-denied. Public installed authoring, registry retention, owned PostgreSQL integration, canonical Run/Task and release qualification remain open.

## Exact canonical guide delta

Target docs/skills/repository-operations.md; add:

“Generated Python result serialization follows Core's Action contract: a result exposing model_dump is converted with model_dump(mode='json') before strict JSON encoding. This permits supported typed model outputs, including nested JSON-mode conversions, while preserving finite JSON, size, exclusive-file and declared output-schema checks. Cover both plain and logical-context generated helpers. A subprocess reproduction against a pinned artifact proves the original defect; focused helper tests do not establish that a rebuilt installed candidate has passed.”

For Robot authoring, endorse the exact documentation-PROPOSAL.patch SHA256 5e2e24732a2a6ce6cc9aec9950ba1ce3be58fab1d790238703901efa3e477d25, with its explicit root integration/qualification limitations retained. Its distinction between receipt consistency and host issuance is mandatory. Do not change remaining-gate wording to completed until root integration tests support it.

Upstream disposition: none. No authorized external mutation target; no upstream defect report warranted by this bounded review.
