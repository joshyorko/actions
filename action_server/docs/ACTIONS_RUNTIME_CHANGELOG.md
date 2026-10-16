# Actions Runtime Changelog

This file is the release-note source for the clean-break `actions-runtime`
distribution, its `actions-runtime-*` tags, and the native Runtime release
workflow. The historical `action_server/docs/CHANGELOG.md` remains the changelog
for the older `action-server-v1.2.x` delivery line and is not used to identify
an Actions Runtime release.

## Unreleased

Runtime 1.0.4 is a source release candidate. Preparing versioned notes and
qualification artifacts does not establish a tag or published release. Publish
1.0.3 and complete its owner verification before promoting or publishing 1.0.4.

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
  guards. Keep published dependency floors and bundled RCC 18.19.3 unchanged.

Snapshots require trusted source namespaces and may include pre-existing files;
they do not promise an atomic tree or exclusive invocation attribution. Runtime
artifact-worker/provider acceptance, full browser issue closure and external
native distribution handoff remain separately gated (#134, #153 and #211).

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
