# Mapped Knowledge compiler admission

Base da928b69e0558917c3e88af9297ddfd3bec818e8, detached isolated
/workspace/actions-knowledge-compiler. No root/GitHub/version/lock changes.

Apply knowledge-compiler.patch SHA256
73ce46bef8b07d5d42a44bf9c4a6bb891202af12025dc22e29530fa78ade74c5
and documentation.patch. Production delta is six lines solely in
package_revision_compiler._validate_invocation_compatibility. After the existing
v3-only guard, every operation of each explicit-invocations requirement passes
knowledge_contract. Old no-invocations v1/v2 paths do not call the new validator.
Both build and retained artifact verification already share this hook, so both
refuse unsupported effect/parameters/result even after a forged manifest is
correctly rehashed. Candidate Core a4 / Runtime a39 floors are unchanged.

Prerequisite knowledge_operations.py was copied byte-for-byte from root for
isolated imports, SHA2568976e635543c5a15fd39fae499668d2ca6ea23c41343c4722fa53b59b7fb5f9d;
it is not included/replaced by this patch. Its earlier helper delivery remains
the source of truth. Existing pinned RCC binary was linked into ignored isolated
bin/rcc-18.19.3 for the ordinary fixture, not downloaded/bootstrap-installed.

## Tests and exact qualification

compile_mapped fixture now declares supported four-parameter search/result_json,
corresponding required input schema, and matching synthetic Action signature and
unit call. Generic requirement/mapping model fixtures remain query-only metadata;
those DTOs intentionally represent contracts not necessarily executable here.
New tests reject four bad contracts during build and retained verification after
recomputing revision identity. A valid empty ingestion mapping also compiles under
v3; unmapped Knowledge metadata remains v2 and verifies with its older SDK pin.

Before production fix, baseline.xml records8failed/1passed: all eight rejection
checks demonstrate the gap. That XML retains full failure messages. Its stdout
log was overwritten by the subsequent old-fixture baseline due a harness log-name
error; the surviving second baseline log was renamed baseline-old.log, not
misrepresented as the first baseline. Original XML receipts are intact.

Initial red/first attempts had missing-RCC fixture setup errors (red19errors;
first5pass/59errors/1skip), retained. Reusing the prepared binary resolved setup.
First complete post-fix inventory:61passed/4failed/1skipped. The four failures were
existing Work Item dispatch-refusal tests whose load-only registry/snapshot lacked
the current selection_for/runtime_plan contract. Baseline-old.xml/log reproduces
all four unchanged-base failures. Parent explicitly authorized fixing only that
old test function. Its updated fixture selects the same package/capability/plan
and still asserts AccessDenied 'not executable'; no product check was weakened.
The comment now describes the missing canonical Work Item output domain, rather
than incorrectly describing the entire RCC runner as none-only.

Final inventory66:65passed/0failed/1skipped in1.15s. Includes old compiler tests,
v1/v2 identity/golden checks and archived old-verifier acceptance/refusal.
Skipped test_genuine_generated_action_rcc_build_import_and_test requires
ACTIONS_PACKAGE_COMPILER_PREPARED_RCC_RECEIPT; no exact receipt was supplied and
no real RCC build was attempted. Fake build/import/test evidence is source-level
compiler qualification, not installed generated execution. Static Isort check,
Ruff format/check, compiler mypy and git diff --check pass. Final old test file
was lint/import checked but not wholesale reformatted; exact function-only diff.

## Documentation improvement

Canonical proposal: docs/skills/repository-operations.md; exact documentation.patch.
Durable learning: mapped operation execution validation is additional to input
mapping validation and must apply on both build and retained verification; legacy
DTO paths stay unchanged. Dispatch-refusal mocks must expose canonical selected
capability/plan identity so tests reach the intended later authority gate.
Evidence: baseline8fail, unchanged-base4fail, final65pass1skip, old identity checks
and static receipts. Stale guidance removed: load-only/absent-runtime-plan mocks
cannot substantiate later unsupported Work Item refusal; none-only comment fixed.
Remaining uncertainty: genuine prepared RCC test remains skipped; installed
Knowledge generated lifecycle and root scaffold acceptance are separate gates.

Upstream disposition:none.
