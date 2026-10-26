# Portable multi-task bundle implementation cut

Root-owned continuation of #130/#135. Not implemented or qualified yet.

Keep legacy CompiledPackageRevision and v1/v2 hashes/readers unchanged. Add a distinct v3 task-bundle value and verifier with bounded source archive, exact per-capability schemas, kind=robot-task, source suite/task identity and explicitly compatible plan digests. Discriminated RCC-task versus direct Robot Framework plan payloads: RCC digests appear only in RCC payload; direct plan pins trusted runner/version/Python/platform contract and no host path. Unknown adapters/versions/fields refuse. Do not let a generic name map point at capability[0].

Admit the new bundle through existing FoundryPackageRevision/Request/Audit/source artifact tables with a new build_evidence schema and version-dispatched reader, not an alternate registry/database. Source identity stays portable; worker-local preparation remains Attempt evidence. Exact capability/plan schema projection is required before any common admission. Legacy generated authoring remains unchanged.

Direct Robot Framework7.4.2 is pinned in the development lock via canonical toolkit; executable available only to a trusted configured test worker. It was verified against primary release metadata at https://github.com/robotframework/robotframework/releases and https://robotframework.org/robotframework/latest/RobotFrameworkUserGuide.html. No model/package-supplied executable plugin, interpreter path or fallback. Environment preparation via RCC for developer tools does not make the direct runtime plan RCC.

Compiler inspection must happen out of process under explicit existing trusted developer admission; Robot library initialization is executable and must never occur in coordinator verification. Bounded static source/task/schema validation plus out-of-process Robot dry-run can establish inspection evidence; do not label a dry-run business execution. Two genuine .robot tasks, distinct input schemas and exact output contract; exact task name restrictions/collision handling must account for Robot's case/space/underscore matching.

Actual tests must execute a direct plan through canonical Run/Attempt/output authority and a separately genuine robot.yaml/RCC task plan, with original mutable directory absent and no plan fallback. Package/admission replay, schema collision, corruption, unknown adapter, cancellation/uncertain launch, artifact retention and restart must remain truthful. If a worker cannot execute a saved plan it refuses rather than generating empty RCC fields or selecting an alternate plan.

Next concrete sequence: bounded artifact value/verifier with old-reader refusal; registry version dispatch and exact projection; direct adapter with existing journal/fence/publication; RCC task adapter; real-worker/Task integration after clock21. No completion claim from this design.
