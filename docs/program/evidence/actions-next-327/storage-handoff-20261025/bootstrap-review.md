# Robot bootstrap/configuration independent review

Read-only current working-overlay review, exact file hashes in source-pins.json.
No blocker found after the integrator's explicit selection-kind dispatch tightening.
No ordinary Robot execution, Task execution, installed acceptance or cross-platform
qualification is claimed. Tests reported by root were not independently rerun.

The optional ACTIONS_FOUNDRY_ROBOT_PROFILE is a bounded, duplicate-key-rejecting,
closed descriptor with explicit trusted-developer-execution admission and absolute
configured direct interpreter and/or prepared RCC receipt. It does not select a
worker or grant an actor authority. Bootstrap rejects a Robot profile without the
existing authorized runtime execution profile. Workspace, worker, policy, provider,
Package, capability and plan deploy grants remain required. Direct plan selection
is allowed only with configured direct Robot and verified retained Robot selection.

Bootstrap wires SqlAuthoringAuthority to registry.evidence, so actual retained
Robot validation is consulted; activation checks every Package's readiness. The
runner dispatch now recognizes RegistryCapabilitySelection for Python and
RegistryRobotSelection with explicit direct/rcc keys for Robot. Unknown selection
or unsupported/unconfigured Robot kind fails closed. Existing Python runner retains
its prepared RCC/logical execution setup. Existing detached Task host still has its
separate RCC runner wiring; this review does not close Robot Task/logical joins.

## Portability proposal (root applies)

Existing marker is pytest.mark.skipif, not a custom Linux fixture marker.
run_outputs/test_filesystem.py uses the Linux descriptor provider predicate
`not hasattr(os, "O_PATH")`; foundry_fixtures.foundry_package_store also skips
non-Linux. Apply module Linux-descriptor marker to test_robot_runtime_runner.py.
All test_robot_registry_validation.py host cases run actual pinned direct dry-runs:
module skip only outside Linux x86_64/Python 3.12. test_robot_validation.py's synthetic
configured fixture constructs RobotValidator/RobotExecution, which requires Linux
x86_64, so module skip unsupported OS/arch; decorate only its three real_direct
cases additionally for Python != 3.12. Missing pinned Robot/dependencies on the
supported platform must remain failures. These exclusions are not Win/Mac passes.

## Storage inventory and proposed commands

inventory.json records all six RCC spaces, exact allocated bytes, bounded receipt
provenance and old a39 frontend dependency size. process-scan.json supersedes the
first process scan: no target refs were observed in readable cmdline/cwd/exe/maps/fd.
Some live sandbox/RCC process cwd/exe/maps were permission-inaccessible. Therefore
these are conditional owner-confirmed candidates, not a universal inactivity proof.
An initial transient codex command-line reference disappeared in the fresh scan.

Known diagnosis candidate:
`/workspace/actions-327-a41/compiler/robocorp/holotree/1c9c512_5a1fac3_170e4263`
allocated 208,908,288 bytes. Proof and RCC receipt retained separately under
helper-diagnosis. RCC 18.19.3 dryrun confirmed exact identity selection:

```
ROBOCORP_HOME=/workspace/actions-327-a41/compiler/robocorp /workspace/actions/action_server/src/actions/server/bin/rcc-18.19.3 holotree delete --dryrun 1c9c512_5a1fac3_170e4263
```

After owner confirms inactivity, the supported mutation is the same command with
`--dryrun` removed. It was NOT executed. Preserve its retained external receipts;
RCC manages the derived space and metadata, not manual removal of arbitrary cache.

Old frozen frontend dependencies candidate (not its source/evidence):
`/workspace/actions-327-a39/installed-combined/source/action_server/frontend/node_modules`
allocated 332,120,064 bytes. RCC does not own npm node_modules, so no RCC deletion
command is proposed for it. Root may remove only this exact directory once inactive;
no deletion was performed here. Combined known candidates: 541,028,352 bytes.

Preserve publish original 643401a_5a1fac3_9fcd2534 (204,406,784 bytes), qualified Core
proof 6f2b9e0_5a1fac3_170e4263 (208,785,408 bytes), and user-controller
8827c57_5a1fac3_9fcd2534 (204,414,976 bytes). Also preserve all artifact content,
materialization/trust, hololib, source and receipts. Two additional derived spaces
8827c57_5a1fac3_170e4263 and 8935607_5a1fac3_170e4263 each use 204,414,976 bytes;
exact dryrun selection works, but bounded retained-log inspection did not establish
their failure-only provenance, so they are not yet recommended for deletion.

The first unconfigured RCC help call reported a read-only default HOME mkdir error;
subsequent list/dryrun explicitly selected the existing a41 ROBOCORP_HOME. No new
home, environment or mutation was created. No storage deletion was performed.

## Exact canonical guide delta

Propose docs/skills/repository-operations.md:

“Robot host preparation is an optional closed descriptor layered on the existing
execution profile. It supplies only explicit direct/RCC preparation and never
worker or actor authority. Runtime dispatch must discriminate verified retained
Package selections and explicit runtime kinds; unknown kinds must not inherit a
fallback adapter. SQL authoring readiness must come from verified registry
retention for every referenced Package. Configuring that dispatcher does not by
itself qualify ordinary Robot Task/logical execution.”

“Pinned Robot dry-run tests skip unsupported OS/architecture and, for real direct
children, unsupported Python versions; missing dependencies on the supported
platform remain failures. Linux filesystem test skips are exclusions, not portable
passes. Storage recovery distinguishes derived RCC spaces from retained artifact,
trust and evidence. Preserve successful publish/Core-proof spaces, use exact RCC
holotree-delete dryruns for proven inactive derived spaces, and state process
visibility limits. RCC is not the cleanup authority for npm node_modules.”

Documentation improvement: exact paragraphs above; evidence source pins, existing
platform predicates, RCC help/list/dryrun and inventory. No cosmetic or diary change.
Remaining uncertainty: actual Robot execution/Task joins and unobservable process
references/failure-space attribution. Upstream disposition: none.
