# Actions Runtime Changelog

This file is the release-note source for the clean-break `actions-runtime`
distribution, its `actions-runtime-*` tags, and the native Runtime release
workflow. The historical `action_server/docs/CHANGELOG.md` remains the changelog
for the older `action-server-v1.2.x` delivery line and is not used to identify
an Actions Runtime release.

## Unreleased

## actions-runtime-1.1.1

- Prepare complete Linux x86-64, Windows AMD64 and macOS ARM64 delivery,
  including CPython 3.12/3.13 wheels, native executables and their checksums.
- Use macOS 26 ARM builders with measured host identity. Preserve the macOS
  12.0 wheel deployment target, signing policy and pinned RCC 18.19.8.
- Keep Core 1.1.0, Work Items 0.5.0, dependency security floors and backend
  feature/storage behavior from 1.1.0. No celld implementation is added.
- Retain Canvas, named queries, Knowledge and managed Work Items on SQLite and PostgreSQL.
- Preserve every published 1.1.0 file, checksum, tag and preparation identity.

All three platforms require actual qualification before publication. Existing
limits on desktop modes, retained-launch reconciliation, recovery and unsigned
native delivery still apply; a new build host does not prove older-OS execution.
Unknown retained launches stay blocked pending reconciliation. Existing upgrades
still require coordinated database backups for rollback; automatic exactly-once
external effects and universal post-launch recovery are not promised.

## actions-runtime-1.1.0

- Add persistent Canvas authoring with immutable revisions, explicit activation,
  scoped capability discovery, and generated Action/Robot execution through RCC.
- Add bounded named data queries and Knowledge operations with DuckDB and
  PostgreSQL bindings, sealed results, authorized paging and artifact access.
- Add managed Work Items with fenced Run/Attempt ownership, explicit approvals,
  durable outputs, and bounded recovery on SQLite and PostgreSQL.
- Fix Canvas inspection replacing app views, persisted v2 result tables, narrow
  layouts, and app reopening after output retention expires.
- Raise affected TLS/JWT/HTTP dependency floors to patched versions and rebuild
  locked native artifacts. Optional backend security qualification stays separate.
- Use RCC 18.19.8, Core 1.1.0 and Work Items 0.5.0. Preserve the legacy API/import
  aliases; upgraded Runtime databases require coordinated backup for rollback.

Qualification and limits:

- This 1.1.0 release delivers Linux x86-64 and Windows AMD64 only. macOS
  artifacts are absent until a later release; unallocated macOS jobs remain
  unverified, not passed. Included wheel/native provenance and security gates
  still apply.
- Real desktop acceptance covers Codex mode in ChatGPT desktop. Genuine
  ChatGPT-mode E1 and native query-result-before-approval are not qualified.
- Cancellation intent is not terminal process-stop proof. Unknown retained
  launches remain blocked pending explicit reconciliation; automatic exactly-once
  external effects and universal post-launch recovery are not promised.
- celld is not implemented or qualified and is not advertised in this release.
  VS Code extension release and native exact-VSIX acceptance are separate.
- Native release assets are unsigned when the existing credential-free producer
  policy applies. Local/source, installed-wheel and native platform receipts
  retain their individual scope and skips.

## actions-runtime-1.0.4

- Forward ordinary string inputs only through the selected trusted Robot task's
  explicit `inputEnvironment` declaration. Reject undeclared/protected names and
  bounded input failures before Run, counter or artifact admission; retain
  Runtime Work Item controls and private temporary task environments.
- Retain bounded snapshots of the configured Robot `artifactsDir` after task
  success or failure. Preserve workload names, authenticated downloads and HTTP
  ranges, and retrieval after source removal and Runtime database restart.
- Correct Windows pathname/descriptor timestamp comparisons without weakening
  identity, mutation, portable-name, link/reparse, hardlink or collection-limit
  checks. Retain already admitted complete files and private collection errors.
- Carry forward the accepted 1.0.3 static-path namespace and streamed Robot form
  guards. Keep declared dependency floors and bundled RCC 18.19.3 unchanged.

Snapshots require trusted source namespaces and may include pre-existing files;
they do not promise an atomic tree or exclusive invocation attribution.

## actions-runtime-1.0.3

- Add bounded Runtime history handling and load current Work Items in the Runtime UI.
- Tighten browser-origin and authentication handling.
- Harden Robot Framework download and archive handling, and refresh Runtime administration assets.
- Keep the declared Core compatibility floor at `actions-core ^1.0.2`.

## 1.0.2 - 2026-09-07

- Correct author and maintainer metadata to Joshua Yorko and replace legacy
  product branding and download links in the PyPI description.
- Preserve existing Runtime 1.0.1 artifacts and tags.

### Fixes

- The clean-break Runtime release uses RCC `v18.19.3` as its primary bundled
  and execution baseline, with RCC `v18.18.1` retained only for N-1 coverage.
- Runtime release artifacts are named and verified as `actions-runtime` assets;
  the existing `action-server` CDN/S3 paths remain compatibility handoff paths.

## 1.0.1 - 2026-09-07

### First publishable clean-break Runtime release

- Defines the Community Actions Runtime package as `actions-runtime` for its
  first public release.
- Uses the `actions-runtime-1.0.1` tag and the generated Runtime PyPI and
  native-release workflows.
- Retains the existing Action Server binary download, CDN, S3 drop-box, and
  Homebrew handoff paths as compatibility delivery surfaces for this Runtime.
