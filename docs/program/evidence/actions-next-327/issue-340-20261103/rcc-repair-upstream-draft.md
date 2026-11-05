# DRAFT ONLY: lifecycle repair JSON may fail with an empty digest after interrupted acquisition

Target: joshyorko/rcc. No issue creation or upstream source changes authorized.
Observed binary: published Linux RCC18.19.7, SHA-256 f8e0394be7f47ee84d6f4cd734822b87b492a4d6102f977f6a18f29453703d48.

In private synthetic fixture homes, bounded acquisition was interrupted after120s.
A later acquisition verified the same artifact. Native lifecycle inspect reported
ready with zero active leases. `rcc env lifecycle repair --artifact "$ARTIFACT"
--provider local --json` returned exit1 for the Robot home with:
`json: error calling MarshalJSON for type environmentartifact.Digest: cannot encode an empty digest`.
The artifact argument was a nonempty canonical sha256 digest.
The Action home separately refused an existing orphan materialization path.
No lifecycle guard was disabled and no protected directory was manually removed.

Retained evidence: robot-lifecycle-repair.stderr, action-lifecycle-repair.stderr,
robot-lifecycle-inspect.stdout, action-lifecycle-inspect.stdout, native-repair.log.
This is an upstream repair/reporting limitation, not proof of an ordinary exec
regression: the same parent import passed with published18.19.3 and18.19.7 in
matched clean homes. The complete publish/acquire/republish/import sequence also
passed for each version when only immutable cache inputs were seeded.

Actions has a separate integration defect: its prepared compiler republishes a
used live cache, allowing snapshot drift despite an unchanged specification.
A fixed trusted prepared binding must retain its original artifact identity.
Do not conflate that failure with this native repair diagnostic.

Exact-phrase read-only issue dedup returned no matches. A minimal state-independent
reproducer and the release that introduced the repair error are not established.
Upstream disposition: draft prepared, not posted.

## Controlled HOME relocation counterexample

The ordinary execution failure is now isolated independently of repair. On
source ab432b12b0ac88039224ec018c3e16f50b63a1f6, one freshly published artifact
`sha256:468071124bde221dca05b869561447c49c159d5e44c0b69a0d22af2001827d7b`
was exercised with the actual compiler's complete sanitized environment,
including `RCC_NO_BUILD=1`. Only the binary or HOME changed:

| Binary | HOME | Exit |
|---|---|---|
| 18.19.7 | original preparation home | 0 |
| 18.19.7 | new empty private execution home | 1, orphan materialization path exists |
| 18.19.7 | original preparation home restored | 0 |
| 18.19.3 | new private execution home | 0 |

There was no Run admission, automatic retry, concurrent execution, guard bypass,
or manual lifecycle mutation. The final 18.19.3 invocation ran only after all
18.19.7 observations; this cache was retired from acceptance use afterwards.

To reproduce against an owned acquired artifact, use the same ROBOCORP_HOME,
artifact, trust carrier, working directory and no-build environment for each
command. First execute with the preparation HOME, then change only HOME to an
existing empty private directory, then restore it. Execute:

```sh
"$RCC" --no-build --workers 2 env exec --artifact "$ARTIFACT" \
  --provider local --permissive-local \
  --trust-carrier "$ROBOCORP_HOME/artifacts/v1/trust" \
  --trust-carrier-type filesystem --json -- python -c 'import os; print(os.environ["HOME"])'
```

The source mechanism is `common/variables.go::SymbolicUserIdentity` hashing
`os.UserHomeDir()`, `htfs/library.go::ControllerSpaceName` prefixing it, and
`environmentlifecycle/materialize.go::materializationID` using that identity.
The added `environmentlifecycle/gc.go::validateProvisionalRecords` path refuses
an existing materialization whose identity differs from the current HOME.
This is a demonstrated 18.19.3-to-18.19.7 compatibility change under HOME
relocation, not evidence that all ordinary 18.19.7 execution is broken.

Actions can respect the stable RCC cache namespace while restoring private
execution HOME inside its trusted Python helpers before user imports. The
integration repair does not require changing RCC or weakening lifecycle guards.
Whether RCC should support multiple HOME namespaces in one cache remains an
upstream contract decision; no upstream issue or source change was made.
