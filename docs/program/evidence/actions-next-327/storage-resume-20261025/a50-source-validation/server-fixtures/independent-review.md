# Independent fixture review: CLEAR

Exact async test SHA256ff923512eac2e23c3a28569fdacc254aacf7af907f1a6dc876a1c5a9c78f4799; full OpenAPI fixture SHA25600d50d7bbe04a66bcc4f054b434ee957c8dada36f0c3ac035684fd64b932a1fd.

Async repair waits up to10seconds for RUNNING after queued admission, retaining original20second sleep and cancellation request/status4 assertions. Terminal states fail through pytest.fail rather than being accepted by polling; the helper catches Exception while pytest failure escapes. No natural completion is accepted as cancellation. This remains status-based active cancellation evidence, not independent child-launch instrumentation.

OpenAPI patch adds exactly three existing managed routes: schema GET, capabilities GET with required workspace_id query, operations POST. Existing fixture contents/assertions unchanged. Source router matches names/methods and validation response. No production authorization mutation.

Root/helper reported two focused passes; reviewer ran no tests/services. Initial origin mismatch and failed broad receipt remain preserved; subset success does not supersede broad-suite failure.

Documentation improvement:
- Canonical file proposed: docs/skills/repository-operations.md.
- Exact delta: “Async API admission may return while Run status is still queued. Active-cancellation tests must wait under a deadline for RUNNING and reject terminal completion before issuing cancellation; do not assume immediate worker startup or accept a naturally completed Run. Full OpenAPI fixtures should enumerate newly registered routes exactly rather than weaken comparison to a subset.”
- Durable learning: distinguish asynchronous admission from observed execution status and schema coverage from subset matching.
- Evidence: two exact source diffs plus wait_for_non_error_condition exception handling and managed router declarations.
- Stale guidance removed: immediate RUNNING expectation and missing managed routes.
- Remaining uncertainty: whole applicable Runtime suite and installed live child lifecycle remain separate gates.

Upstream disposition: none; stale local fixtures only.
