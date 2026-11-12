# Storage handoff — WIP, not a qualified release

This checkpoint preserves the sole integrator's unfinished Robot integration after the owner directed a fresh-container handoff. Parent baseline: `9df42b54c3c790c53b3a9a1cd96ad16579236986`, tree `1b88a3fdc2562c15aebf45badc8bf70a951613d4`. The commit containing this file is the handoff source identity; obtain its full SHA/tree from Git, not the older installed wheel identity. Existing campaign remains #327 / draft PR328 / release/327-invoice-vertical-20261020. No release or merge authorization.

## Saved state and qualifications

- Applied Robot authoring/validation, retained registry validation, standalone runner, explicit host profile/bootstrap, and SQL-only receipt projection/validator. Source hashes are in source-hashes.json. This combined source is WIP: public logical-receipt hooks and Task/Work Item Robot dispatch are unfinished. Ordinary execution must not be claimed qualified.
- Receipt validator: 118 passed (59 SQLite + 59 PostgreSQL), zero failures/skips; first disk-floor interruption retained. Synthetic adapter and real SQL/output seals, not genuine Robot/RCC execution. Exact inventory/log/XML in robot-receipts archive.
- Registry validation: 118 passed, zero skips. Standalone runner: 34 passed, zero skips, synthetic adapter with real authority/provider races. Authoring: 44 focused passed, actual direct dry-run; actual RCC validator NOT_RUN after disk guard. Joined authoring/configuration: 55 passed. Bootstrap regressions: 7 passed, 5 unconfigured PostgreSQL skips; four-source type check passed.
- Last root platform-marker edits and the combined replacement receipt modules have not been rerun together. Full package/type/installed gates remain open. The receipt projection explicitly anticipates an admission validation-field decoder extension; reconcile it with the new registry envelope before enabling hooks.
- Failure lifecycle patch is UNAPPLIED/HOLD, not part of implementation. Decode failure-HOLD.tar.gz.b64 for exact patch, receipts and preserved failures. Its review identifies a possible descendant cleanup race after an early empty process snapshot. Fresh-container barrier reproduction and correction/re-review are required before applying. No successful installed failure lifecycle claim.
- Serialization fix is already committed at 1eca22efe6f7201166c15f84a8d0de05aea03aad, but no rebuilt installed candidate includes its proof yet.

## Exact artifacts, separate from WIP source

Failed installed a41 candidate source: f905c3888ecb448dbce80ce57a9b59ff041eb148. Runtime wheel SHA256 fcf70e1f1cc3b91409dd8600622161085281f968b868373d5b62df10e0c4a661; Core a5 0c1421f7b7cd0db447c82e58458107c92f22051b29eb128c8b765219b863a3ec; Work Items a2 72ef55fc0a7f766fb5d7e4925f8c15bb8211e781b598096ebe9617e1ecad9feb.

Credential-free wheel/build/locked-consumer bundle: Library `libfile_316ad90e466081919f30eb5d1a763309`, actions-327-a41-f905-handoff-wheels.zip, 15,634,209 bytes, SHA256 836e091024a9d34de36ab27bacfab624612e47327edcb947eacb283bdaa6947c. This is explicitly FAILED Canvas execution evidence: BaseModel JSON serialization failed; original browser timeout and missing terminal receipt remain failures. Fresh locked consumer passed 66 active distributions, pip check, exact wheel members and MCP initialize only. Never substitute this for full installed acceptance.

Previously passed a39 Dakota host-specific bundle remains Library libfile_1141c898e8248191be6ac4a95cb69734, SHA256 2a138243181a80a748842b3c7ae88b186856a421da1c5aea1ee4542b2c002745. See recovery-a39/dakota-handoff/agent-prompt.md. Owner launches local test; preserve Executor. No tunnels/credentials/local dispatch authorized here.

## Fresh executor procedure and ownership

Fetch the existing release branch and verify final handoff commit/tree against parent receipt. Read AGENTS, repository skill and current #327 ledger. Bootstrap the pinned RCC18.19.3 / Poetry2.1.1 toolkit via developer/toolkit.yaml; use task-local writable caches. Do not copy credentials, producer datadirs, trust keys, huge caches, or historical traces. The exact wheels are transferable; compiler preparation must be rebuilt with target-local trust and its actual new identity recorded.

Evidence archives are base64-encoded gzip tar files; verify decoded hashes in archive-hashes.json before extracting into an isolated task directory. They contain selected inventories, exact commands, source patches and logs. Local historic command gateway was `source /workspace/actions-cloud/activate.sh`, then `rcc task script -r developer/toolkit.yaml -- python /workspace/actions-cloud/package-command.py action_server run ...`; helper run scripts retain exact arguments. Reconstruct supported fresh toolkit paths rather than assuming producer-local paths exist.

All three helpers are being frozen for transfer: knowledge_host (generated failure patch), knowledge_review (registry/runner/reviews), robot_authoring (authoring/receipt validator). No helper may resume writing without new integrator allocation. Final parent receipt confirms stopped ownership. Parent appoints exactly one fresh integration writer; do not create another branch/PR or parallel integration owner.

Immediate critical path: review saved combined WIP, reconcile receipt projection/admission validation envelope, implement existing logical receipt/ticket hooks without provider IO inside SQL, finish canonical Robot Task/Work Item breadth and races; reproduce held cleanup issue; rebuild corrected installed Canvas v2 and retain real generated execution/artifact/restart/rollback evidence. Continue Knowledge, security, distribution and owned dependency closure without silently narrowing full scope.

Independent lane restrictions persist: B's denied installed evidence publication and C's denied input/docs publication require their precise approval; do not retry through another route. Celld NO-GO; real ChatGPT and Codex host gates remain separate. Vendor audit gaps remain in mandatory logging/truststore, basic scaffold/browser, optional agent/vendor endpoints, test executable downloads, legacy fallback and development tooling. Preserve secret suppression and attribution; no other-repository mutation approval inferred.

Rollback for this WIP: inspect this commit's parent and use a new reviewed revert checkpoint on the existing branch; never reset/force-push shared history. Installed a41 is not a deployment recommendation. No production state was changed.

Upstream disposition: none. This is a storage recovery checkpoint. Original failed, skipped and interrupted evidence is preserved; component passes do not qualify the combined installed product.
