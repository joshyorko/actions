# Independent static review: a44 recipe correction

**PASS for the narrow recipe correction; not execution approval or browser qualification.** No qualification module was imported or executed. Review used ZIP byte reads, hashes, Python AST parsing and textual browser-source inspection only. No keys, grants, server, browser, install or RCC workload was created.

Verified immutable bundle SHA256:
`37ab0cf8bf66132c0112e5b65c7528a1092f4665ac7f7d32a022ec2ee77d18b0`.
Original recipe SHA256:
`6444546dfdbd8d271d046f9758c4addeb34e0eef4ae8bafc12d633c6153329c6`.
Corrected recipe SHA256:
`90d2ae610bd521a70785ef3bfb9238aa0719b12a8887c68d6a2d6aa4c5ae0f86`.

The byte diff is exactly three single-occurrence replacements: source assertion 730f277ce13bd3a123c854c85c1c9fc2c185096c → d0c87a38a937cc339e8e661ac453c7a62ed41fa6; docstring a42 → a44; final receipt label a42 → a44. recipe.patch exactly reproduces the diff. After normalizing those three string constants, original and corrected ASTs are identical. No guard, control flow, grant behavior or process command changed.

The corrected source assertion matches bundled source-sha.txt and candidate.example.json. AST Runtime/Core assertions match config: Runtime 1.1.0a44, Core 1.1.0a6. All three bundled wheel bytes independently hash to both wheels.json and candidate config values. The original bundle is unchanged; no wheel mutation occurred. review-evidence.json retains exact wheel hashes and assertions; review_static.py is the reproducible read-only check.

## Execution and approval boundary remains unchanged

- Importing/running qualify.py is side-effectful: top-level config reads and Node invocation, fixture creation, automatic synthetic bearer generation, then asyncio.run(main()). It must not be imported as a harmless identity check.
- Execution still starts local Runtime/host processes and calls public authorize-local dry-run/apply/replay to create grants, then later revokes a deployment read grant. This review does not authorize those actions in any other environment or replace required target-specific approval.
- The recipe still invokes its Playwright browser-preflight and browser driver. Both retained scripts request chromiumSandbox:true; neither contains --no-sandbox. No managed CUA adaptation was introduced or claimed. Existing sandbox/approval restrictions remain; this correction supplies no alternate execution route.
- The config's existing execution_authorized=true flag is data, not an independent grant of permission. Target-local artifacts/trust, host bytes, browser availability and any applicable approval must still be satisfied.
- The original strict recipe's disk floor remains 5 GiB, unchanged. The 10 GiB floor applies to this producer executor's bounded workloads and preparation measurements; it is not a newly imposed requirement for the separate browser-only consumer. The parent reports that consumer has less than 5 GiB free, so it cannot execute the original strict recipe under its existing guard. Any managed-adapter capacity plan requires separate review; this narrow correction changes no capacity guard.
- Existing E1=false and “actual ChatGPT not tested” statements remain. Corrected identity does not establish host UI or ChatGPT acceptance.

Documentation improvement:
- Canonical file proposed: docs/skills/repository-operations.md.
- Exact delta: “Before handing off an immutable installed candidate, statically compare the qualification recipe's source/Runtime/Core assertions with its bundled config, source-sha.txt and measured wheel hashes. Use AST/byte inspection rather than importing side-effectful qualification scripts. A recipe-only identity correction must preserve the original bundle and record both recipe hashes; it does not authorize automatic credentials/grants, adapt Playwright to a managed browser, relax sandbox policy or change product wheel identity.”
- Durable learning captured: independently verified recipe identity and side-effect boundary.
- Evidence: review-evidence.json, exact recipe.patch, immutable ZIP wheel checks and unchanged browser sandbox options.
- Stale or ambiguous guidance removed: outdated a42 source/labels in the scratch recipe; original evidence remains immutable.
- Remaining uncertainty: target execution approval, supported sandboxed browser and complete host UI qualification. The separate consumer reportedly has less than the unchanged strict recipe's 5 GiB floor; any managed-adapter capacity plan remains a separate review. The producer executor's 10 GiB workload floor does not transfer to that consumer.

Upstream disposition: none. Local packaging/recipe mismatch; no upstream defect conclusion or external mutation.
