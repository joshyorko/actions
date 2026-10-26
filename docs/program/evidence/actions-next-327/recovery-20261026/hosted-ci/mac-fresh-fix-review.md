# Read-only review of macOS fixture-boundary corrections

Reviewed the current diff in the five requested test files. I found no production or workflow changes in this correction set. The new guards align with the actual Linux-only provider contract and are at shared fixture entry points before filesystem mutation/construction:

- `test_local_provider_setup.py::provider` checks `sys.platform` before creating its blobs/input fixture state. This fixture is imported by the local-knowledge/logical proof tests; its module consumers cannot rely on the defining test module's marker.
- `test_invoice_review.py::reviewed` checks before creating a schema/objects and directly constructing `FilesystemOutputProvider`; it supplements, rather than replaces, the module-level skip that only marks tests defined in `test_invoice_review.py`.
- `test_provider_catalog.py::local` checks before creating the root, opening its descriptor, and constructing/staging a provider.
- `test_runtime_task_bootstrap.py::test_default_off_and_policy_without_runtime_fails` now asserts and returns when the factory returns `None` off Linux. The Linux-only assertions and missing-policy failure remain unchanged on Linux.

The concrete guard stays in `FilesystemOutputProvider.__init__` and no auth checks, provider assertions, publication checks, strict DSN behavior, or Linux test bodies are weakened. This is a narrow shared-fixture boundary correction, not a module or family-wide skip. The three parameterized regression cases exercise early skip for imported fixtures. The two new factory checks cover Darwin and Windows and verify unsupported-platform return occurs without creating native state. `git diff --check` is clean. I did not rerun tests because the parent is already running the requested affected-module plus capability set; their reported red/green counts remain parent-owned evidence.

Canonical guidance already says shared Linux-only fixtures must check their own platform because module-level pytest marks do not propagate to imported fixtures (`docs/skills/repository-operations.md`, existing portable-CI guidance). Optional, narrow clarification: append the three fixture names as examples to that paragraph, to anchor the reusable rule. No doc change is required for correctness; avoid turning this into a broader platform support claim.
