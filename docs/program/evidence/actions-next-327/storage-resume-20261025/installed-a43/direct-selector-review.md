# Direct Robot Canvas selector review

Observed installed result supplied by integration owner: a43 RCC Robot synchronous PASS/FAIL and detached Tasks pass; direct Robot canvas_get fails at GenericCanvasView._selected's RCC-only selector before execution. This is not a direct execution failure.

Read-only proposal review: preserve select_rcc_execution_profile for activated Python. A separate select_canvas_execution_profile may admit direct Robot only after the same common resolver/identity/sole locked default/profile checks, plus canonical FoundryPackageRegistry selection_for(exact capability, exact plan) returning RegistryRobotSelection whose retained plan is direct. Avoid catch-AccessDenied-and-fallback, which would accidentally retry permission/profile failures as another runtime.

At initial inspection, production selector implementation was unchanged and the new direct test was being authored; this receipt is not approval of an unseen final patch. Existing contract_tests/test_execution_profiles.py tests cover authorization, locked-default policy, profile identity, plan mismatch and RCC-only rejection. New test_canvas_profile_accepts_only_verified_direct_robot covers real direct Robot acceptance, legacy RCC selector rejection, and wrong selection type rejection.

Additional focused adversarial cases proposed:
- valid alternate registry/DB passed in registry kwarg must not substitute for deployment authority's registry;
- retained RCC Robot plan paired with forged direct snapshot must reject;
- ordinary direct Python selection and duck-typed registry reject;
- profile mismatch/revocation and nonlocked plan reject on direct wrapper too;
- corrupted Robot admission carrier rejects; stale active app scope rejects before route selection.

Documentation improvement:
- Canonical file proposed: docs/skills/repository-operations.md.
- Exact delta: “Direct Robot Canvas qualification must open the app and retrieve its bound model through the public canvas_get route before testing execution. Invocation descriptor discovery alone does not prove the Canvas model's execution-profile selector accepts that runtime. Keep the activated generated-Python selector RCC-only; broaden Canvas selection only for an artifact-verified Robot package and retained direct plan, preserving exact Deployment/default-plan/profile authorization checks.”
- Durable learning captured: discovery and bound Canvas selection are separate gates.
- Evidence: installed failure reported by root; generic_view.py _selected; execution_profiles.py; existing and newly authored profile tests.
- Stale or ambiguous guidance removed: treating descriptor discovery or RCC Robot success as proof of direct Canvas usability.
- Remaining uncertainty: final selector patch and installed corrected direct route still need verification; claimed Robot Work Items remains HOLD.

Upstream disposition: none. Local integration failure; no external mutation.

## Final patch read

Reviewed the written execution_profiles.py/generic_view.py diff. No confirmed blocker: both wrappers share unchanged exact identity, locked sole default, profile equality and common authorization checks; direct route requires the same canonical deployments._packages registry, RegistryRobotSelection, matching package/capability/plan references, and retained direct plan kind. GenericCanvasView passes its existing output capability registry. activated_execution.py still calls the RCC-only selector. No permission-failure fallback was introduced. Root reports 17 SQLite passed/17 PostgreSQL deselected before further adversarial cases; this lane did not rerun. Installed corrected direct acceptance remains pending.
