# Integrated a50/Core8 source validation

Base checkpoint 5b9c70e00e5e019a751aec5385591e5a2bbd615e; these receipts cover the integrated working tree, not an installed candidate.

- Complete Core suite: 449 passed, 5 skipped, 4 warnings (100.59s).
- Claimed Task and existing Task SQLite regression: 95 passed, 145 deselected, 1 warning (30.06s). PostgreSQL was not selected.
- Runtime configured lint/typecheck PASS, 649 source files.
- Contract check FAILED: 45 passed, 2 failed. Basic template and clean-wheel Core minimum assertions retained old versions. Those expectations were corrected to Core8; the clean-wheel test archives HEAD and must be rerun after the new source is committed. No replacement pass is claimed here.
- Prior full a49 remains FAILED: 4299 passed,197 skipped,3 deselected,5 failures.

Reviewed logging public bridge preserves object identity/redaction; optional child tracing resolves only when requested. Reviewed server fixes update the OpenAPI fixture and replace a 0.2-second scheduling assumption with bounded status polling.

Next: committed-source clean wheel checks, PostgreSQL claimed Task regression, new a50/Core8 installed Task and cancellation, then complete applicable Runtime qualification.

Upstream disposition: none; local integration and fixture corrections.
