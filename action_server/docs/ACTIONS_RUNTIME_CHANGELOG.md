# Actions Runtime Changelog

This file is the release-note source for the clean-break `actions-runtime`
distribution, its `actions-runtime-*` tags, and the native Runtime release
workflow. The historical `action_server/docs/CHANGELOG.md` remains the changelog
for the older `action-server-v1.2.x` delivery line and is not used to identify
an Actions Runtime release.

## Unreleased

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
