# Documentation proposal: provider reader error classification

**Canonical file:** `docs/skills/repository-operations.md`

After the existing provider-startup-reader paragraph (currently ending “Join errors remain fixed secondary classes attached to the original startup failure.”), add this sentence only after the implementation separates the two exception paths:

> Join-call failures are recorded as `PROVIDER_JOIN_*`; final thread-liveness query failures are recorded as `PROVIDER_ALIVE_*`. Either leaves reader cleanup unconfirmed when liveness cannot be observed.

**Evidence:** The source-bound 4-case F949 RED / 6-case 3812 GREEN controls and `alive-classification-control.json`. A one-shot `Thread.is_alive()` failure currently reproduces a mislabeled `PROVIDER_JOIN_OSError`; the core cleanup stays incomplete and grants no tree authority.

**Stale or ambiguous guidance:** The guide currently describes join errors but not the distinct liveness-query error path. Do not integrate this wording until the code fixes the misclassification.

**Remaining uncertainty:** No full package suite or cross-platform CI was run.
