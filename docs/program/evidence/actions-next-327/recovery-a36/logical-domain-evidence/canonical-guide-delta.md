Canonical file: docs/skills/repository-operations.md.

Replace the preparation-component paragraph beginning "ConfiguredProviderExecution and LogicalExecution qualify" with:

`ConfiguredProviderExecution` and `LogicalExecution` provide bounded eager logical
preparation. The standalone and generic Work Item output wrappers accept an
explicit per-invocation logical binding for atomic publication; this domain
checkpoint does not itself wire ordinary bootstrap or generated RCC execution.
Preparation resolves exact retained Deployment bindings and artifact-verified
requirements, supports only selected parameterless data `.scan/v1` reads, and
refuses declared aggregate output above256KiB or more than32operations before
engine calls. Child context version `actions.logical-read-context/v1` contains
logical lookups only. Host-private provider/config/catalog pins never enter the
child context or public receipt. Public logical summaries contain context/result
hashes, immutable source/contract digests, operation identities and row counts.
Only an issued preparation object may authorize publication; it must be released
by its host lifecycle owner after completion/abort and cleanup. Serialized
context or summary is neither restart authority nor a grant.

Replace "It must be integrated inside the existing domain output publication
transaction, alongside independent queue/Run guards, not called as a substitute
transaction." with:

The standalone and generic output wrappers call this recheck inside their
existing publication transaction, alongside independent queue/Run guards and
before base publication or queue finish. Enter
`outputs.bind_logical_execution(execution, prepared)` outside any SQL transaction;
it caches verified immutable operation expectations and Package digests. The
binding must cover staging and publication, rejects nested/reused live bindings,
and is cleared in finally. It requires the same canonical base output service,
registry, database, actor, AttemptFence and snapshot. The new guard uses cached
artifact expectations and SQL pins, with no artifact, filesystem, engine or
secret I/O. Existing unrelated v1 authorization/schema code is unchanged.
The host releases the issued object only after the binding exits and native
cleanup has settled; uncertain cleanup remains a separate runner obligation.

Add immediately after this section:

### Bound generated execution receipt boundary

Version selection comes from artifact-verified capability requirement IDs.
Zero-requirement dispatch and terminal records keep v1 bytes and behavior; a
bound dispatch uses v2. V2 launch and terminal records carry `logicalReads`;
the dispatch top level has no such field. Launch-less v2 is only a pending
seed, never evidence of execution. Publication requires exact equality with the
issued preparation summary, matching retained launch/execution, independent
Run/Attempt and optional Work Item fences, and the measured four-output inventory.
Missing binding or a cloned/unissued preparation fails closed. This checkpoint
does not allow direct bound terminal publication replay without fresh issuance;
existing read-only terminal APIs perform retained validation instead.

Retained standalone, managed generic and Task reads validate closed canonical
v2 carriers, versions, operation coverage, immutable Deployment/provider/source
identities, declared operation row limits, launch/terminal summary equality,
lineage, stream measurements and canonical SQL output seals. Retained projections
read artifact-verified Package metadata and common SQL metadata, never source
seals, private catalog/config, engines or secrets. Existing read authorization
and actual sealed-byte resolution remain necessary. Identity validation cannot
recompute historical logical result/context hashes from a public summary and
must not be described as cryptographic proof of issuance. Exact alias-key
prevalidation remains required by the retained Pydantic regression.

Documentation improvement:
- Durable learning: guard entry must cache immutable artifact expectations before the publication transaction; the active binding owns no lifetime beyond finally, while the runner owns prepared-object release and uncertain cleanup.
- Evidence: frozen.xml70PASS across SQLite/ownedPostgreSQL and codec tests; guard-final.xml10PASS; v1-regressions.xml64PASS/125deselected. SQL-only test forbids registry.load, factory.check_current and open_provider during the new guard and verifies live revocation refusal.
- Stale ambiguity removed: preparation is now joined to domain publication guards and retained readers, but not by itself to native runner/ordinary installed execution. Summary structure alone is not full receipt authorization.
- Remaining uncertainty: root-owned runner/bootstrap/detached seed join, native cleanup supervision and installed unchanged-Package two-provider acceptance remain separate; Knowledge/full Data gates remain open.
