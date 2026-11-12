# Core a7 qualification

Core source version1.1.0a7. Observed HEAD d0c87a38a937cc339e8e661ac453c7a62ed41fa6; qualified-source-sha256.txt records manifest, agent client and new boundary-test bytes. No source edits, installations, DB workloads or RCC environment publication by this lane. Initial disk free15GiB, reserve10GiB.

Commands through prepared RCC gateway:

    actions run env ACTIONS_TRUSTSTORE_TEST_PYTHON=/workspace/recovery327/dependency-review/truststore/consumer/bin/python pytest -q --junitxml=/workspace/recovery327/logging-independence/a7/core-full.xml
    actions run invoke lint
    actions run invoke typecheck

Static receipts: core-lint.log PASS (Ruff check,190 files formatted, isort). Optional Markdown linter unavailable and not run. core-typecheck.log PASS, no issues166 files. Full-suite authoritative result is core-full.xml/core-full.log; completion result appended below.

## Exact canonical documentation proposal (root applies)

Target docs/skills/repository-operations.md, optional endpoint/dependency qualification:

“Optional Agent integration requires an explicitly configured endpoint. Test that missing or empty owned configuration fails before network or PID-file discovery; owned configuration takes precedence over an explicitly supplied legacy variable; and an inaccessible selected endpoint does not silently fall back. Run these boundary tests in the full Core suite with the isolated truststore consumer selector, followed by the package's configured lint and typecheck. Keep source-suite results separate from frozen installed candidate acceptance.”

Documentation-improvement receipt: new test_agent_client_boundary.py explicitly spies on PID discovery and network probes and verifies precedence/fail-closed behavior. Static passes recorded above; full result appended below. This removes ambiguity between compatibility with explicitly supplied legacy configuration and implicit discovery/default endpoints. Installed a44 gates remain frozen prior-candidate evidence; a45 installed gates stay root-owned.

Upstream disposition:none. Owned optional-integration qualification, no confirmed upstream defect; external reporting draft-only and no target/publication.

Completed full Core result:453 passed,0 skipped,4 inherited ast.Str deprecation warnings in103.49s. RCC exited0 with no leftover-process warning. This includes all5 new explicit Agent endpoint boundary cases and isolated truststore selection. Qualified manifest/client/test hashes still match at completion. Final disk free15GiB. No source changes proposed or required by this run; no active lane workload remains.
