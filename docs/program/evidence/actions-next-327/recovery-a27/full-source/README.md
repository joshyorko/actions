# Frozen a27 complete source gate

Source `4ef00f0a6ea35a901733d10385e74054f20dfe24`; engine unchanged from `fdc38d7090c4ac470171c499e77eab636fd452e6`. All eight required stages passed with zero skips: managed158, storage299, components168, invoice129, worker134, compiler22, generated52, effects72. Full portable Runtime passed2634, skipped21, deselected290. Exact JUnit and logs are retained.

The21 portable skips comprise eight native Windows cases, eight generic RCC opt-in cases, three upload/publication cases, one explicit RCC artifact vertical, and one pinned task-input case. The generic cases passed8 separately in `../actual-generic-rcc`; the pinned task-input case passed in the required worker stage. Other skipped cases are not promoted by this receipt. All owned PostgreSQL cleanup passed. Compiler and worker RCC artifacts remain retained.

Command: prepared gateway `python action_server/scripts/verify_invoice_queries.py --compiler-receipt /workspace/actions-recovery-327/compiler/prepared.json --worker-runtime /workspace/actions-recovery-327/evidence/a27-full/1494b48e-735a-4598-9c8b-24e3a703c839/worker-runtime.json --evidence-dir /workspace/actions-recovery-327/evidence/a27-full --worker --generated --effects --full`, with task-owned compiler-view cleanup enabled and separate pytest log output.

The bounded receipt retains input hashes, imported module provenance, pinned environment identities and full skip classification; its raw-receipt digest covers the locally retained large RCC member inventory. This source qualification does not establish later draft integration, installed browser acceptance, authenticated ChatGPT, or complete campaign release. Upstream disposition: none.
