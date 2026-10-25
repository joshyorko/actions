# Installed output HTTP probe preparation

`lane_b_installed_output_http.py` performs real HTTP requests to an explicitly
supplied numeric loopback origin. Its caller supplies an independently qualified
installed server, exact retained handle and expected bytes. It does not start a
server, provision identity, revoke grants or access SQL/providers directly.

```python
probe = OutputHttpProbe(base_url, installation_owner_credential,
                        workspace_id, handle, expected_bytes,
                        app_session=actual_app_session)
before = await probe.qualify()
# Stop/perform/record authorized operator revocation outside this helper.
after = await probe.after_revocation()
```

Positive GET must return200, exact bytes, no-store and nosniff. Missing/invalid
credentials, actual AppSession-only credentials, another Workspace and unknown
handle must be denied; Range must return416. Redirects are never followed and
environment proxy settings are ignored for this owned loopback test. An absent
positive route is FAIL, not a skip. Optional AppSession coverage is NOT_RUN if no
actual token is supplied. Failure receipts retain status/hash/length/error class,
never credentials or request URLs. Revocation requires a successful positive
baseline, and its receipt does not itself prove which grant the caller revoked.

Validation:21 simulated local HTTP contract tests passed, with tracing disabled;
stdout/XML retained. Ruff, configured formatting and Isort passed. These tests
are explicitly simulated and do not establish installed authentication, grants,
publication or download acceptance. Actual installed use awaits host wiring of
the reviewed factory. The configured installation owner bearer must satisfy both
outer middleware/endpoint dependencies and the managed callback; arbitrary
managed tokens do not bypass the outer output-route gate.

Command (prepared package-local Poetry):

```bash
poetry run pytest -p no:robocorp_log_pytest \
  tests/contract_tests/test_lane_b_installed_output_http.py \
  --junitxml=/workspace/lane-b-state/receipts/http-output-simulated.xml
```

Rollback removes the two new helper/test files; no persistent state is changed.
No PR metadata update was attempted for this slice.

Exact proposed canonical delta for `docs/skills/repository-operations.md`:

> Output HTTP qualification requires the configured installation owner bearer
> accepted by both ordinary middleware and the managed authenticator. An arbitrary
> managed credential is insufficient. Require positive GET200 with exact retained
> bytes before interpreting denial probes; a positive404 is a failed routing/download
> gate. Record optional AppSession checks as NOT_RUN when no actual token is
> supplied. Post-revocation readback requires separately recorded operator revocation
> and performs no SQL mutation itself.

Learning: positive readback and explicit credential context prevent false denial
success from missing routes. Evidence: helper and local HTTP refusal tests;
existing `_ConfiguredAPIKeyMiddleware` path boundary. Uncertainty: installed route
wiring and producer lifecycle remain separate unexecuted gates here.

Upstream disposition: none.
