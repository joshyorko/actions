# Independent Core PR248 admission and package credential probe

## Verdict

**Core PR248 source/admission: PASS for integration; publication remains blocked.** Reviewed exact head `71f55ddd1ce34720db0e13433a2f1f5c9eed70a0` in `/workspace/work/community-resume/wheel-inventory`. The branch was clean and the exact-head checkpoint records all five hosted workflows PASS. This review does not authorize or perform a tag, merge, or publication.

## Core source and release review

- The final delta from previously reviewed Core checkpoint `df7b0d664a661fcab5d014092f4259c32e74590f` consists of an 11-line Actions logging-test import-order fix and the repository-operations guidance. No Core package source, API, package metadata, or lock projection changes were introduced by that final delta.
- The PR’s versioned runtime integration surface preserves object identity by re-exporting the existing Core implementations. Tests exercise public `ActionContext` and `ActionsListActionTypedDict` exports, lazy import/discovery, `__all__`, server-integration re-export identity, and managed request injection. The thread-local parameter-conversion scope tests cover absence outside a scope, nested-scope rejection without losing the outer value, cleanup on exceptions, thread isolation, and fresh scope state.
- The Core dependency declares `actions-http-helper = "^1.0.0"`, which admits 1.0.3 under its `<2.0.0` upper bound. More importantly, the exact Core candidate wheel was installed into a fresh environment with Helper constrained to 1.0.3 through pip's configured index. The receipt’s resolver URL is `https://files.pythonhosted.org/.../actions_http_helper-1.0.3-py3-none-any.whl`; the resolver archive hash equals the independently checked PyPI/GitHub release digest `46ed7ce0e0d3e2e05456d937b5b24bc9dfa0d7d4b98f8119b9fdf00d4fa7e9f9`. Both imported distributions resolve from the temporary environment, with no Helper `direct_url` marker, and clean `actions list` and `actions run` pass. The separate local-wheel compatibility receipt is not used as registry evidence.
- Candidate Core 1.0.2 wheel hash is `9d527edf540978172178894546add75f117f240786aec804cb75c308615a7e80` (101,410 bytes), bound to the exact subject head. `verify_index_resolution.py`, its receipt, pip report, and the independent registry-compatibility receipt were read; the two candidate artifact files were rehashed and matched.
- Exact-head hosted checks are PASS: AI audit `37976580100`; HTTP Helper Tests `37976580071`; RCC developer toolkit `37976580074` (six primary/N-1 OS jobs); Actions Core Tests `37976580109` (Linux, Windows, macOS); Actions Runtime PyPI Release `37976580171` (all platform wheels/source). The last is a pull-request event and its credential/publish steps were skipped.
- `actions_release.yml` runs verification before publishing. The publish job is tag-only, checks community ancestry and package/tag version agreement, downloads the verified artifact, validates its inventory/digests, then invokes the publisher with `PYPI_TOKEN_ACTIONS_CORE`. No tag or release was created during this review.
- The exact registry-index proof addresses the compatibility risk: pip selected the published Helper wheel by URL and SHA and ran a Core consumer from that isolated installation. It does not itself prove successful Core publication or post-publication registry readback.

A documentation limitation remains: the new generated `actions.server_integration` API page links its “Link to source” anchors to `sema4ai/actions/tree/master`; the pre-existing generated API page has the same historic generator output. This does not affect package source or runtime compatibility and was not changed by this bounded probe. Proposed follow-up: configure the API-doc generator to bind source links to the maintained community repository and the versioned release source, and regenerate the pages; avoid hand-editing only this generated page.

## Core/Runtime PyPI credential availability

No prior successful Core/Runtime nonempty-availability receipt was found. The existing workflow checks only covered Helper; the exact Core PR Runtime workflow ran as a pull request and skipped both credential and publication steps.

A separate branch-push-only probe was committed and pushed on `release/package-credential-availability-20261009` at `7501198b3cbd834a79c132d398abb5e05c852582`. It has `permissions: {}`, one job in the `pypi` environment, no checkout, installation, registry client, authentication, upload, or publication step. It tests only whether the Core and Runtime secret variables are empty and emits only state labels. No `workflow_dispatch` trigger exists.

Exact hosted run: [37978559166](https://github.com/joshyorko/actions/actions/runs/37978559166), head `7501198b3cbd834a79c132d398abb5e05c852582`, conclusion **FAIL** because Core was empty. The log reports Core unavailable/empty and Runtime nonempty. Registry authentication, token scope, and upload were not attempted for either package. The Runtime nonempty result is presence only and is not publication permission. No credential value was read locally or recorded. The hosted environment masks secret values in its log.

The exact workflow shell block passed synthetic controls: both sentinel values nonempty exits successfully; Core empty with Runtime nonempty and both empty exit unsuccessfully; every case reports only empty/nonempty states and never emits synthetic sentinel values. Result record: `/workspace/work/community-resume/release-lane/package-credential-check-shell-validation.log`.

## Upstream disposition

- Candidate repository, owner, and consumed version/revision: No upstream defect candidate was investigated. The Core candidate is Actions Core 1.0.2 at `71f55ddd...`; the runtime dependency under compatibility check is published Actions HTTP Helper 1.0.3 with the hash above.
- Classification and evidence: No defect classification; the focused earlier proxy 403 remained an Actions test-environment observation and was not attributed to an upstream defect.
- Deduplication searched (issues and pull requests): Not performed because no upstream defect candidate was under investigation.
- Disposition: No confirmed upstream defect; no issue filed or updated.
- Maintainer decision/follow-up trigger: None.
- Downstream issue, gate, or consumer affected: Core publication and Runtime/native promotion remain dependent on separate release gates.
- Temporary mitigation owner and removal condition: None.
- Remaining uncertainty: Core credential is unavailable in the `pypi` environment. Runtime credential presence does not prove authentication/scope. Actual publication and registry readback remain unverified.

## Documentation improvement receipt

- **Canonical file changed:** `docs/skills/repository-operations.md` on probe branch `7501198b...`.
- **Durable learning captured:** A safe pre-tag presence probe belongs in a separate short-lived workflow bound to `pypi`, with no repository permissions, checkout, setup, shell tracing, token output, or registry request. A nonempty secret is not evidence of PyPI authentication, scope, or upload permission.
- **Evidence:** Exact Helper precedent; probe workflow structural validation; synthetic empty/sentinel controls; exact hosted Core/Runtime availability result; publication workflow boundaries.
- **Stale or ambiguous guidance removed:** None. The paragraph distinguishes credential presence from registry and publication authorization.
- **Remaining uncertainty:** The nonempty-only probe leaves authentication, scope, and upload permission untested. No package suites were rerun; exact-head hosted gates and attached receipts were used.

## Credential-probe attempt 2 update

After this review was written, attempt 2 of the same run (`37978559166`, job `113984244155`) completed successfully. The native operator confirmed both Core and Runtime secret variables were nonempty; attempt 1's empty-Core result remains a valid historical failure. This probe reports variable presence only and performs no authentication or upload. Core 1.0.2 PyPI preflight returned 404, and root is proceeding through the normal immutable release workflow. This addendum does not assert a pushed tag, successful publication, or registry readback. Exact attempt-2 run receipt: `core-credential-attempt2.json`.
