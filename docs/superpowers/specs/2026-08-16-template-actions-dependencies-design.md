# Template Actions Dependency Refresh Design

## Goal

Ensure every shipped action template resolves publicly available Actions
libraries when a user rebuilds it.

## Changes

- Pin `actions-core=1.0.0` in every template `package.yaml`.
- Pin `actions-work-items=0.4.4` in the producer-consumer template.
- Leave `actions-http-helper` transitive through Core and exclude
  `actions-runtime`, which is the server distribution rather than a template
  library.
- Add a static contract test that enumerates shipped template manifests and
  rejects stale Actions dependency declarations.
- Record the template dependency policy in the canonical repository operations
  guide.

## Verification

The focused contract test must fail against the current `actions-core=1.6.4`
and `actions-work-items>=0.2.4` declarations, then pass after the manifest
updates. Run the surrounding contract-test module and `git diff --check` as
final local gates. Package rebuilding remains the user's next step.

## Scope

This change does not regenerate template archives, locks, or package builds,
and it does not publish any distribution.
