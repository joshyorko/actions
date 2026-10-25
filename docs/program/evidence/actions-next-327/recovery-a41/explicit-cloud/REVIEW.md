# Explicit cloud endpoint and template publisher review

Disposition: no blocking finding in current bounded root diff. Read-only source review, no independent test rerun or root edit.

`_storage.get_hostname` now rejects absent storage and empty/whitespace hostname with an actionable validation error, preserving an explicitly stored hostname exactly. Storage-load errors no longer fall through into an implicit vendor choice. `_ask_user.ask_user_for_hostname` catches only the expected missing-endpoint validation error, then requires nonempty valid input; blank input may select only an existing explicit default. No DEFAULT_CR_HOSTNAME references remain in Runtime source/tests. Inspected callers are cloud/package-cloud operations, not ordinary local server startup.

The new cloud test verifies missing/empty refusal, explicit hostname preservation, prompt retry and no HTTP GET when cloud-list lacks an endpoint. Whitespace-only storage is implemented via strip() but not directly parameterized; adding it is useful small coverage, not a code blocker.

Current diff removes both deploy-beta-templates.yml (automatic community templates path plus dispatch) and deploy-templates.yml (manual production publisher). Both referenced the same unowned template role/bucket; deletion changes source reachability only and performs no settings, credentials, cloud resource or remote mutation. The workflow test prevents those concrete role/bucket paths from returning. This review does not classify all remaining vendor links or infrastructure.

Exact canonical guide delta, target docs/skills/repository-operations.md:

“Legacy cloud compatibility commands require an explicit endpoint, supplied by the caller or retained configuration. Missing, empty or whitespace-only stored endpoints must fail before HTTP requests; the prompt may reuse only an explicitly configured default and must not choose a hosted vendor automatically. Preserve explicit operator choices rather than silently rewriting them. Retiring repository workflows that publish templates to unowned role/bucket targets removes source reachability; it does not modify cloud settings or qualify a replacement publishing service.”

Evidence: reviewed current helper/prompt/caller changes, request-trap test assertions and both deleted workflow definitions. Remaining uncertainty: installed/cloud compatibility flow is not rerun; whitespace-only test coverage recommended. Upstream disposition:none, local policy/compatibility correction.
