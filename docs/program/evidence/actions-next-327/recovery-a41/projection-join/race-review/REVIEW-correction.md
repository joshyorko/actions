# Projection correction re-review

Reviewed correction SHA256 `76e9de0d14118e1522e9f0d3fdd854deb84554d61da49ca51f2d82044466dd3b` atop original backend `413ca4d446e5d683ba03fe58158cbf79f09d0e6e319b69a4fb40fc8f7fd83c8d`.

Approved for the reported **during-provider-read preimage mutation** fix. The helper now compares complete Run, RunPin, RunAttempt, optional RunExecutionIntent row presence/content and all attached RunOutput descriptor preimages, rather than only selected result identity/digest/size. Added preimage reads and final comparison are SQL-only; existing `outputs.resolve` still opens its provider descriptor under the existing grant-lock transaction, then streams/closes outside it. This patch neither changes that lock contract nor adds provider IO to `current()`.

Independent original reproducer now passes: `race-fixed.log` and `race-fixed.xml`, **1 passed, 1 deselected** (SQLite). Previous `race.log`/`race.xml` failure remains. Helper's inspected retained evidence reports 20 red / 2 passed mutation cases across SQLite+PostgreSQL followed by 70 passing / 0 skipped full component cases. Those are helper receipts, not an independent rerun of all 70. Earlier fixture/trap failures and tests3 logs are now included in correction delivery.

Remaining integration limit: the preimage starts in helper.current(), after route `_read` validates the full generated receipt. This correction does not itself bind that earlier validation across the intervening boundary. For an end-to-end claim, capture/pass the validated preimage or reuse the existing prebound SQL receipt validation at the helper boundary. Root has this limitation. Route/session/provider-trap and adapter/browser tests remain separate; no installed claim.

Exact canonical guide delta (replace the review's pending-fix wording):

“Generated result projection compares complete SQL-owned execution/output preimages before and after reading the selected sealed JSON. Selected output digest equality alone does not detect changes to other receipt fields during provider IO. This comparison protects the helper's read interval; callers must separately bind the full validated generated receipt to that interval. The helper's rechecks use SQL only, while existing output resolution acquires the provider descriptor under the read-grant lock and streams outside it. Preserve both the failing mutation receipts and corrected results; source/component race closure does not qualify app routing or installed rendering.”

Upstream disposition: none. No root changes or external actions.
