# Wave 5 additive correction

This correction supplements [wave 5](actions-swarm-mk3-20261010-wave5.md) and
its original evidence manifest. It does not rewrite the attempt receipts or
change their original gate statuses. The correction evidence manifest is
`../program/evidence/wave5-correction-20261010T2112Z/manifest.json`.

## PR304 browser evidence is separate from PR305 Canvas evidence

The passing pinned Playwright result belongs to PR305's Canvas bridge test. It
remains unchanged and says actual ChatGPT/production-host acceptance was NOT
RUN. It is not #153 Origin/ambient-session evidence.

The separate corrected PR304 #153 attempt selected exactly one case on Linux
against source checkout `73605934c1c948895410a5abaed6c225a396e038` and the
retained frozen binary SHA-256
`08aa825cb3b6bc8ec0d3747f2323de89d18f5df42bc78d72c934579648e0a85e`. The
pytest case failed at native server startup: the staged executable looked for
`_internal/libpython3.12.so.1.0`, which was absent from the staging directory.
The browser was not launched. This is a packaging/staging failure observation,
not a product source defect. No actual ChatGPT run, production authorization,
or cross-platform #153 acceptance is claimed. The earlier setup attempt that
failed to import `psutil` is retained as a separate attempt; it is not merged
with this selected-case result.

## RCC warm attempt 2 readback correction

The original task receipt and `interpretation.md` are preserved byte-for-byte.
The first interpretation's statement that the truncated tail could not yield
verified acquisition is superseded by the additive
`acquire-readback-correction.md` and Sol's independent readback. Scoped
read-only recovery found a complete nested `verification` object with
`valid: true`, the expected digest
`sha256:d78a6bdc62558ab7d8b97df55fb3071eefe1c497bb8afe769490d8e324e86d16`,
and matching consumer B `ready.json` and `verified-content.json` metadata. The
object SHA-256 is `04b03fb319022ad00e260fa46ce1be1c61b288aea26d88e5ca3faa7e436fb808`;
the ready and verified-content object hashes are
`ea6c954caab0bf73a69d05e07396441e680f68bdd0fc48efda85aba24e482675` and
`8d4e32aaa51a8588cce1e7531da661492c7d8fe6d17a588ffa85955f137f2c28`. These
exact objects and the 44,195-byte raw task receipt (SHA-256
`56b7e0b40b79b2d9630400dd39eb2209935623d9e17f4fc4644bdcd7adae22af`) are
included in the correction evidence directory. Sol's readback review is GO
for this scope (JSON SHA-256
`c077506b65d72b747f359812e6d2b4f5ecf9da948d4c1f88605bf2c2cd05c8d4`).

Only that nested object and the named consumer metadata are recovered. The
truncated outer response still does not establish the full JSON payload or
`cacheHit`; the original strict automatic gate remains
`PREFLIGHT_OR_RUN_FAILURE`. The recovery did not rehash every indexed
environment content file and did not run `env exec`. Sol's scoped result review
is GO for this readback and HOLD for execution acceptance. No retry, provider
comparison, full #134 acceptance, or RCC defect is established.

## PR308 replay inputs and canonical guidance

The correction evidence also retains the exact PR308 candidate-version task
configuration, corrected RCC runner, prepared toolkit and setup files referenced
by its 37-pass/1-deselected readback. The independently reviewed result is a
candidate-verifier/unit result only; provider-backed Runtime acceptance remains
NOT RUN.

`docs/skills/repository-operations.md` now records the verified durable lessons:
bind candidate version, wheel filename, embedded `METADATA` and measured bytes;
retain the actual outer Python `sys.prefix` and module origins instead of
inferring the active environment from executable realpath; keep unknown fields
unknown when recovering a nested object from truncated outer JSON; stage the
complete adjacent frozen-executable support tree; and report the RCC release
version actually pinned by the developer toolkit instead of asserting that it
is perpetually the latest stable release. No source or dependency pins changed.

Upstream disposition: none. No production defect or external report is claimed.
