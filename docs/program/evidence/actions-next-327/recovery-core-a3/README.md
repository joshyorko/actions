# Private Core a3 logical lookup SDK

Core 1.1.0a3 adds public actions.data.scan and explicit private context installation. No provider, filesystem or environment lookup occurs in scan. The context is closed, canonical, digest-checked and bounded, with ContextVar isolation and fresh row copies.

Canonical RCC developer gateway: /workspace/actions-recovery-327/run-prepared python /workspace/actions-cloud/package-command.py actions. Commands: install; run inv lint; run inv typecheck; run pytest tests -q --junitxml=/workspace/actions-recovery-327/evidence/core-a3-tests-final.xml; build --format wheel --output /workspace/actions-recovery-327/core-a3-wheel. Full Core suite: 375 passed, four dependency deprecation warnings, 52.26 seconds. Configured lint and type checks pass. Initial invocation with unsupported --robocorp-log-output exited before tests; retained separately and corrected without that option.

The private wheel was built and measured, not published. This is source/API qualification. Genuine rebuilt RCC consumption, Runtime lifecycle/publication join and unchanged-Package two-provider execution remain open. Existing public Core RCC preparations are not evidence for the new SDK. Runtime dependency metadata has not yet been refreshed while another owned qualification uses that environment.

Documentation improvement: docs/skills/repository-operations.md records the explicit installation boundary, canonical numeric and operation bounds, isolation, and requirement for actual measured private-wheel RCC qualification. No existing installed-execution claim was promoted.

Upstream disposition: none.
