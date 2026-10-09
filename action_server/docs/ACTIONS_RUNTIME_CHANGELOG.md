# Actions Runtime Changelog

This file is the release-note source for the clean-break `actions-runtime`
distribution, its `actions-runtime-*` tags, and the native Runtime release
workflow. The historical `action_server/docs/CHANGELOG.md` remains the changelog
for the older `action-server-v1.2.x` delivery line and is not used to identify
an Actions Runtime release.

## Unreleased

### 1.0.3 candidate — unpublished

The source candidate includes bounded Runtime history handling, stricter
browser-origin and authentication boundaries, safer Robot download/archive
handling, refreshed Runtime administration assets, and current Work Items
loading. Its worker integration requires the Core 1.0.2 API. Canvas remains an
independent frontend entrypoint; this candidate does not claim a Canvas authoring
or execution feature.

The package dependency releases are available: Core 1.0.2, HTTP Helper 1.0.3,
and Work Items 0.4.4. Runtime 1.0.3 itself is not published. PyPI Runtime 1.0.2
and native Runtime 1.0.1 are separate release lines; no native 1.0.3 assets are
available.

Known acceptance gaps: issue [#134](https://github.com/joshyorko/actions/issues/134)
remains open because the provider-backed offline-warm RCC acceptance fails
closed on provider HTTP 503; the selected-provider 503-before-execution negative
passes, but this does not prove warm reuse or full RCC acceptance. Issue
[#153](https://github.com/joshyorko/actions/issues/153) still requires its
real-browser acceptance. Actions issue
[#211](https://github.com/joshyorko/actions/issues/211) remains open pending
external verification of the native release handoff. The candidate has no
Runtime release tag or published Runtime artifacts; package, browser, security,
and native-platform release gates remain outstanding.

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
