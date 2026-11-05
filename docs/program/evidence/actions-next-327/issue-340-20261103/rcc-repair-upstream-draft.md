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
