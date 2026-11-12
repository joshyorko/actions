# Draft only: local provider alias selects an HTTP trust carrier

No upstream mutation is authorized. This is a factual draft for `joshyorko/rcc`,
not a filed issue or a release acceptance waiver.

## Summary

RCC 18.19.3 accepts the built-in `local` filesystem provider for environment
artifact publication, but provider-bound acquisition/execution without an
explicit trust carrier fails before the child task runs. The same artifact,
provider and verification policy succeed with the generated filesystem carrier.

## Reproduction

Prepare an owned local home and a package with `spec-version: v2` and
`dependencies: {conda-forge: [python=3.12.15]}`. Use the released RCC 18.19.3
binary, build the artifact with `env publish --environment package.yaml
--provider local --json`, and retain its returned digest.

```text
rcc env acquire --artifact <returned-digest> --provider local --permissive-local --json
Error: artifact trust attachment verification failed
```

The persisted verification receipt reports `valid:false`, `code:invalid`,
`policyMode:permissive-local`, and diagnostic
`trust attachment could not be decoded`.

For the same artifact, keep both original flags and add:

```text
--trust-carrier <owned-rcc-home>/artifacts/v1/trust --trust-carrier-type filesystem
```

Acquisition then returns `verification.valid:true` with provenance, SBOM and
revocation digests. The verification policy digest is unchanged. No keys,
signatures, trust roots, credentials or security settings were changed. The
negative was also observed on actual `env exec` before the invoice task ran.

## Environment and evidence

- Linux amd64, glibc-compatible owned environment, released binary SHA256
  `7e588c01751ca2ae15ba13ef67f2f4b7567697a5a8389737059a73936f509428`.
- Consumed tag source `4148c2b71705c9d2baf0e88b48d08a79cb7bda0f`.
- Minimal Python-only artifact
  `sha256:7aac67f3c44b5cffd54c5f4f50be6836f315ff95d87e950a94140010fda50df2`.
- Candidate-SDK artifact
  `sha256:478b98a390625e9a440a85b343236e040f0e18c59a4034fa1d5ef3d33f8eb678`.
- Retained downstream logs and JSON under
  `/workspace/actions-327-state/evidence/worker/`: `local-prepare-correct.*`,
  `minimal-local-rejection.*`, `minimal-local-positive.*`, `acquire-local.*`,
  `acquire-explicit-carrier.*`, and `execution-carrier.log`.

## Pinned source finding

[`optionalEnvironmentTrustCarrier`](https://github.com/joshyorko/rcc/blob/4148c2b71705c9d2baf0e88b48d08a79cb7bda0f/cmd/environmentTrustPolicy.go)
returns `HTTPCarrier{BaseURL: providerURL}` for any nonempty provider when no
carrier reference is supplied, including `local`. The
[HTTP carrier](https://github.com/joshyorko/rcc/blob/4148c2b71705c9d2baf0e88b48d08a79cb7bda0f/artifacttrust/carrier.go)
requires an HTTP(S) URL. The
[lifecycle wrapper](https://github.com/joshyorko/rcc/blob/4148c2b71705c9d2baf0e88b48d08a79cb7bda0f/environmentlifecycle/trust.go)
replaces that underlying error with the generic attachment-decoding diagnostic.
The inspected `main` implementation had the same selection logic; no newer
binary was executed or accepted.

Expected behavior is that the supported local provider can use its generated
local carrier without being interpreted as an HTTP endpoint, or that the CLI
reports the required carrier explicitly. Maintainers choose the correction.
This is a fail-closed correctness/compatibility finding, not evidence of a trust
bypass.

## Reporting disposition

Searched open/closed issues and PRs for `"trust carrier" local`; six related
issues and zero PRs were returned, with no exact duplicate established. Related
history includes [#126](https://github.com/joshyorko/rcc/issues/126) and
[#208](https://github.com/joshyorko/rcc/issues/208). Read the contribution guide
and bug template. Initial untyped issue searches returned API422 and were
corrected with explicit `is:issue` / `is:pull-request` filters.

Downstream owner is the Actions #327 integration lane. Its narrow mitigation
adds an explicit local filesystem-carrier argument while retaining the provider
and policy; it is rejected for nonlocal providers. Removal requires an approved
RCC pin whose automatic local-carrier selection passes the same negative and
positive cases. Generic remote-provider/warm-trust behavior remains unqualified.

Upstream disposition: confirmed pinned-source compatibility finding, draft only
pending target-specific reporting authority and final duplicate review. No issue,
PR, credential, trust-root or external repository mutation occurred.
