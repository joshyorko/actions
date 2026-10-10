# Local source prerequisite review

Read-only source acceptance advice at integration `31239cf99c7b264a0eab89660e93b391532ac305`, tree `d2ef7229651b6120db5cfa5995c65942ef768da8`. This is a proposed scoped criterion, not implementation approval or full issue acceptance.

The next legitimate prerequisite is one shared source snapshot admission policy. Reuse `ActionPackageHandler.create_runtime_source_snapshot` for generation copying/signature/revalidation, `PackageExcludeHandler` for existing selection semantics, the Robot ZIP portable path predicate for Windows reserved names plus NFC/case collision checks, and `_directory_publication.rename_directory_no_replace` with identity-owned staging cleanup. Extract reusable rules from their current owners if necessary. Do not add a second Package/Robot registry, compiler engine, Deployment model, cache/provider authority or staging lifecycle.

Current source facts:

- Runtime snapshots copy in-root file-link referents, reject directory links, hash included relative path/full supported permission bits/file bytes, exclude default Core/generated-cache and Runtime-state paths, and revalidate source/copy/selected generation. Legacy external pythonpaths remain external. These defaults are compatibility behavior.
- The flat generation key additionally binds current package name. It is a local Runtime cache key, not an approved portable source-artifact or Package Revision digest.
- Package archive building honors authored packaging.exclude. Runtime snapshot creation presently uses default exclusions instead. One inclusion policy cannot be inferred from the other.
- Robot archive admission rejects portable path ambiguity, links/special archive entries and applies byte/count/time bounds. Its publication code copies into a private parent and uses no-replace rename plus owned cleanup.
- Robot copied-metadata validation and Runtime repeated pathname hashes do not establish no-follow root confinement or coherent copying against hostile concurrent replacements. The existing guide already records that limitation. Directory rename itself is publication, not source/root identity admission.
- Slice1a approval comment6094862388 permits strict canonical JSON and typed scoped values only. It explicitly excludes Package compiler, resolver and object-specific digest preimages. Package schema remains experimental.

Proposed implementation boundary for root approval:

1. Preserve existing Runtime legacy policy and cache key behavior exactly. An explicit portable profile may tighten selected/protected input rules without silently changing ordinary CLI imports.
2. Treat the caller-selected root and staging-parent identities as protected input. Metadata cannot choose destination/provider/cache roots. Reject links, hardlinks and special files among selected/protected inputs; excluded trees must not be followed or read.
3. Require relative portable names, NFC/case collision checks across every directory prefix, and protected root declarations/environment/entrypoint inputs that exclusion rules cannot hide. Do not rewrite authored paths silently.
4. Choose canonical executable mode policy, empty-directory treatment, byte/count/depth/name/time limits and source/profile identity framing explicitly before portable digest claims. A concrete conservative option is Linux admission first, reject non-NFC selected names, ordinary files normalized to0644/0755 according to an explicit executable bit and reject privileged mode bits. These are proposed choices, not approved policy.
5. For hostile-input admission, use no-follow confined file/directory reads and opened-object identity checks; verify selected bytes/modes and staged inventory, revalidate reused snapshots, publish atomically and clean only owned failed candidates. Unsupported native enforcement must fail clearly instead of claiming portability.
6. Output a source-only verification/inclusion receipt. It records the admitted profile and exact included bytes, excludes host/runtime paths from portable identity, and says executable inspection did not run. Do not populate PackageRevisionId/RuntimePlanDigest, synthesize capabilities, mark an environment ready, invoke RCC or publish Deployment/provider state.

Meaningful cheap proof includes two equivalent trees at different paths/timestamps/order yielding identical canonical inventories; byte/exec-mode/inclusion changes yielding different intended identities; case/NFC-prefix collision; protected manifest exclusion; link/FIFO/file-directory replacement; source root or parent replacement; mutation during copy; corrupted reused snapshot; and cleanup preserving a replacement staging occupant. Existing legacy fixtures must remain unchanged. Archive/download, compiler discovery, RCC-first consumer, provider, Workspace authorization and actual native platform gates remain separate.

Exact canonical guide proposal

In `docs/skills/repository-operations.md`, after the existing Runtime snapshot identity/retention paragraphs, add:

> Runtime source generations are local executable-source cache objects. Their directory key binds the current package name and included source signature; it is not a portable source-artifact digest, Package Revision ID or Runtime Plan digest. The legacy snapshot policy retains in-root file-link compatibility and supported permission bits, while package archive building separately honors authored `packaging.exclude` rules. Keep those existing defaults unchanged when introducing portable admission.
>
> A portable local-source prerequisite must reuse the existing generation/staging lifecycle and Robot path/publication rules under an explicitly approved profile. Repeated pathname hashes and no-replace rename alone do not prove no-follow root confinement against concurrent replacement. Source-only verification must record its inclusion/link/mode policy and whether code inspection ran; it does not establish capability compilation, Runtime Plan readiness, RCC provider support or Package/Deployment publication. Slice1a canonical JSON and reference parsing do not approve object-specific digest preimages.

Durable learning is the distinction between existing executable cache identity, archive inclusion and portable source admission. Existing Robot race caveats already cover pathname limitations, so retain them rather than duplicate or remove them. Remaining uncertainty is the exact portable profile, digest framing and native enforcement scope to be approved by root. Upstream disposition: none. These are Actions-local architectural prerequisites, not confirmed maintained dependency defects.
