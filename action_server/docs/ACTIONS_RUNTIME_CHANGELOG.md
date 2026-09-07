# Actions Runtime Changelog

This file is the release-note source for the clean-break `actions-runtime`
distribution, its `actions-runtime-*` tags, and the native Runtime release
workflow. The historical `action_server/docs/CHANGELOG.md` remains the changelog
for the older `action-server-v1.2.x` delivery line and is not used to identify
an Actions Runtime release.

## Unreleased

### Fixes

- The clean-break Runtime release uses RCC `v18.19.3` as its primary bundled
  and execution baseline, with RCC `v18.18.1` retained only for N-1 coverage.
- Runtime release artifacts are named and verified as `actions-runtime` assets;
  the existing `action-server` CDN/S3 paths remain compatibility handoff paths.

## 1.0.0 - 2026-09-07

### First clean-break Runtime release

- Publishes the Community Actions Runtime package as `actions-runtime`.
- Uses the `actions-runtime-1.0.0` tag and the generated Runtime PyPI and
  native-release workflows.
- Retains the existing Action Server binary download, CDN, S3 drop-box, and
  Homebrew handoff paths as compatibility delivery surfaces for this Runtime.
