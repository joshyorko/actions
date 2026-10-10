# Historical readiness receipt status

`readiness.json` and `readiness.md` in this directory were created from the Core-only `a70993fa` checkout. Root review rejected the downstream-source analysis as stale. Preserve those files as historical evidence only; their status is **INVALID_FOR_CURRENT_RUNTIME_SOURCE** and they must not drive Runtime release or Homebrew decisions.

Invalid conclusions: they treated retired `Sema4AI/homebrew-tools` as the owner; called Homebrew proof optional; and proposed changing the expected published Core version to latest 1.0.3. The current maintained tap is `joshyorko/homebrew-tools`; Homebrew install/upgrade proof is required, and Runtime's declared minimum remains Core 1.0.2. The canary resolution must be pinned to the exact 1.0.2 floor and verified from the published wheel.

Corrected source-bound evidence is in `runtime-readiness-corrected.json` and `runtime-readiness-corrected.md`.
