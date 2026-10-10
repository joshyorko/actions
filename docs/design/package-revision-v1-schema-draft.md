# Bounded Package Revision schema draft

**Status: experimental schema and fixture only.** This checkpoint implements
the accepted #130 reference-envelope prerequisite, not the full Package v3
design or production authoring syntax. The live [#130 issue](https://github.com/joshyorko/actions/issues/130)
and [accepted scoped prerequisite](https://github.com/joshyorko/actions/issues/130#issuecomment-6094007327)
remain the acceptance authority.

The portable manifest shape is described by
[`package-revision-v1.schema.json`](package-revision-v1.schema.json). It holds
logical package identity, source artifact identity, Runtime/Core compatibility,
typed capability declarations, logical binding requirements, and declared
Runtime Plan headers with environment requirements and a namespaced opaque
adapter-specification digest. Deployment-specific scoped references are kept
separately in [`package-revision-references-v1.schema.json`](package-revision-references-v1.schema.json).
The latter uses a full `PackageRevisionRef` containing Workspace, logical
Package, and immutable revision identity; its `RuntimePlanRef` nests that full
reference with plan digest, plan schema version, and compatibility digest. The
consumer envelope contains only `runtimePlanRef`; its nested
`packageRevisionRef` is the sole owning package reference. A duplicate outer
`packageRevisionRef` is rejected even when it matches the nested reference.
This removes a contradictory source of identity instead of claiming that JSON
Schema compares the two references.

The experimental JSON names map to the semantic fields in the
[#129 domain draft](deployment-revisions-draft.md#workspace-and-scoped-references):

| Experimental reference field | #129 domain field or identity |
| --- | --- |
| `packageRevisionRef.workspaceId` | `PackageRevisionRef.workspace_id` |
| `packageRevisionRef.packageId` | `PackageRevisionRef.package_id` |
| `packageRevisionRef.revisionDigest` | `PackageRevisionRef.revision_id`, a `PackageRevisionId` |
| `runtimePlanRef.packageRevisionRef` | `RuntimePlanRef.package_revision` |
| `runtimePlanRef.planDigest` | `RuntimePlanRef.plan_digest`, a `RuntimePlanDigest` |
| `runtimePlanRef.planSchemaVersion` | `RuntimePlanHeader.plan_schema_version`, a `PlanSchemaVersion` |
| `runtimePlanRef.compatibilityDigest` | `RuntimePlanHeader.compatibility_identity_digest` |

`revisionDigest` preserves the same complete Package Revision identity value as
`revision_id`. It does not select a mutable tag or substitute the source artifact
digest or Runtime Plan digest. The portable `identity.revisionDigest` names the
same identity without adding Workspace scope to package content. Readable
Workspace and package keys in these fixtures are experimental test identifiers;
they do not approve the paused #129 production UUID/API syntax.

Both `runtimePlanRef.planSchemaVersion` and a portable Runtime Plan's
`schemaVersion` are positive JSON integers. The package's draft schema token
and `adapterSpecification.schemaVersion` are separate fields and retain their
own string forms. Structural validation does not establish that a plan schema
version is supported by a registry. A future consumer must check registry
support and resolve plan digest/schema/compatibility identities against the
owning immutable manifest.

The portable fixture deliberately contains no Workspace or Deployment IDs,
resolved binding references or values, credentials, provider URLs, Worker
Profiles, local paths, or Runtime selection/default/fallback policy. A package
declares only logical binding requirements and compatible plans. Deployment
binding resolution and no-fallback Run/retry pinning remain owned by #129 and
#83; dynamic adapter admission and payload conformance remain owned by #143.

The fixture's `sha256:` values are syntactically valid examples, not calculated
Package Revision or Runtime Plan digests. The test pins the canonical JSON bytes
of the fixture for reviewable change, but does not define a production digest
algorithm, cross-language canonicalizer, or signature format. The JSON Schemas
check structure and closed-object boundaries; they do not resolve cross-object
IDs, prove canonical array ordering, validate adapter payloads, compile source,
or prove Runtime execution. Those are separate design and implementation gates.

The focused contract tests use the Action Server's existing `jsonschema`
dependency:

```bash
cd action_server
poetry run pytest -q tests/contract_tests/test_package_revision_schema.py
```

Passing this test proves only that the experimental fixtures satisfy their
schemas and that installation/deployment fields are rejected from portable
content. It also proves that duplicate outer package owners and non-positive
or non-integer plan schema versions are rejected. It does not close #129 or
#130 and does not prove RCC, uv, Python, or
Robot Framework adapter behavior.
