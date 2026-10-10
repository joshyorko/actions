# PR302 exact portability delta review

GO for head `e8e8a9db1c762b31fb4c4f625168dc7337235483`, tree `0392a8b0e5976bb489b53a198240b0d561ee3ad9`, parent `e31506239fd0260d708a11440762537334f8d2d1`, scoped to the two expected argv path strings. Merge admission remains HOLD pending new-head hosted checks.

The expected executable and environment strings now use `str(Path(...))`, matching the producer's existing argument construction on each platform. Exact argument order, provider, single invocation and same-publication spec/artifact assertion remain intact. No production source, assertion relaxation, path normalization, dependency or separate inspection-preparation code changed. Whitespace check passed; owner checkout clean. No blocking finding.

Remote PR302 head matched; at observation 18 checks were pending (16 queued, 2 in progress), mergeable true/unstable. Reviewer ran no tests for this two-line delta and does not claim fresh Windows or actual RCC inspection acceptance. Strict7eca preparation and its fresh type result remain separate.

## Documentation proposal

Add to RCC publication-pair verification guidance in `docs/skills/repository-operations.md`:

> When an RCC argv contract test passes synthetic `Path` values to a producer that uses `str(path)`, derive the expected executable and environment strings from the same `Path` values. Keep the full ordered argv, provider, invocation count, and same-response publication-pair assertions exact. Do not normalize production arguments or relax equality to accommodate Windows rendering; mocked synthetic paths establish argv construction, not path existence or real RCC execution.

Evidence: exact two-line delta, unchanged producer and prior actual Windows expectation failure. This removes ambiguity about portable expectations and mock-versus-executed proof. New-head hosted Windows and actual inspection remain unverified by reviewer.

Upstream disposition: none. Companion JSON records exact commands and bounded observations.
