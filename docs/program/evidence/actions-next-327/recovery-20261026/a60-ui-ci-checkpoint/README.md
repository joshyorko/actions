# a60 UI and CI correction checkpoint

Coverage515/run40370948150 passed at exact PR head
`daf41283a8507b4807c404a1683add9c3750d456`, tree
`e27a3b6b1338913f7c241b5f891b94891034435c`. Its merge was
`2d663366643456b59b076a1d12b4084fb2171c35` with that same tree.
Runtime passed5349/58 skips; Core449/5, HTTP Helper12, devutils335,
Work Items285/46 with10 expected failures; preflight Toolkit225 passed.
Owned PostgreSQL cleanup and receipt upload passed. Baseline recording was
not requested. Exact percentage/inventory totals remain in the unread uploaded
artifact; the passing source gate does not claim installed/subprocess completeness.
The [terminal receipt](coverage-515.md) retains attribution and native failures.

## Measured fixes

Runtime393's macOS and Windows integration each failed one MCP inventory
assertion: native Canvas was expected despite its existing Linux-only private
provider. Custom-resource and missing/wrong-auth tests remain active. The fixture
now requires Canvas on Linux and requires its absence elsewhere. Eight resource
controls first produced4 failures/4 passes; with the fix plus bootstrap default
control,9 passed and1 unconfigured PostgreSQL case skipped. No platform admission
or production authorization was weakened.

Ubuntu Runtime393 passed5351 portable tests/56 skips, then the published-Core
browser case failed at its strict clean-source assertion1025. The bounded
diagnostic exposed the exact assertion; the particular dirty tracked path is
unknown. The source gate now runs after dependency-only npm/OAuth preparation and before tracked frontend
embedding, native build and test phases. The tracked `_static_contents.py` is a
known generated build output, so the earlier post-frontend order was insufficient.
Four final ordering controls first produced1 failure/3 passes at that boundary;
all230 Toolkit cases now pass. Frontend embedding uses its supported `--no-install`
option after the single locked dependency install. The clean-source,
pytest/JUnit, source/worker/browser and cleanup admission checks are unchanged.

The exact frozen a59 Canvas resource passed controlled empty Canvas/library/Canvas
transitions, malformed-library refusal, keyboard focus and tested light/dark axe
checks. It FAILED narrow text overflow. Its 455-character text value forced a
300px viewport beyond3800px; the committed source regression reproduced overflow
with a wider unbroken value before the full-text-preserving fix. The CSS makes
grid contents shrinkable and paragraphs naturally wrap, retaining table/log
scrollers and strict validation. The new browser assertion passed on rebuilt
source without a CSS overlay. Existing host tests keep their original resource
selection; the temporary diagnostic override is not shipped.

This product change advances Runtime to1.1.0a60. Core/Work Items and dependency
pins stay unchanged. Frontend287 tests passed; Canvas203 passed/1 existing skip;
frontend lint/types/format/topology/UI-system checks passed. The focused browser
passed. Configured Runtime lint/typecheck and lock checks passed. This checkpoint
has source proof only: a60 wheel build, clean consumer and exact-wheel browser
qualification are the next gates, not results already obtained.

## Parallel mandatory work

The `data/` receipts preserve direct installed a59 CSV/Parquet and persisted
SQLite registry/authorization/DuckDB passes, including ungranted caller,
revocation, bounds and cancellation. They do not prove immutable compiler-created
Package/Run admission, PostgreSQL, paging/export/cost or expiry. The retained
fixture lacks an admitted Data Package/Run; fake compiler evidence is not a substitute.

The `recovery/` receipt preserves a bounded a56 native datadir copy restored with
the installed a59 helper and two fresh store projections. Source and restored
hashes match. This cancelled fixture has an expired Task and zero RunOutput;
there was no authorized API replay, artifact read or native object relocation.
The earlier a59 PostgreSQL/object and independent cold-RCC components remain
separate passes. Whole coordinated Runtime restore stays open.

The `security/` receipts qualify installed traversal refusal and worker environment
construction only. They do not establish child/file/network isolation or complete
live-host authorization. The source/full acceptance matrix stays controlling.

The PostgreSQL role/password/grant setup was rejected before execution. No SQL,
container, credential or setting change occurred. Its corrected proposal is
preparation only, unapproved, and retains unresolved TLS-network/image watchdog
capabilities and cleanup limitations. It must not be executed or rerouted without
specific action-time authorization. The protected Codex-home denial is also
unchanged; no permission/auth/session transfer or workaround is authorized.

The mandatory ledger separates engineering checks, environment/approval blocks,
actual owner ChatGPT render/invoiceE1 and final publication approval. Optional
celld research is not added to required release work. A57/Dakota remain unchanged.
No public merge, release, package publication or deployment occurred.

Canonical repository operations guidance now records source-gate ordering,
platform-specific inventories, exact resource/layout qualification, layered Data
proof, native restore limits, installed negative boundaries and proposal limits.
All lane proposals were consolidated there. Upstream disposition: none.
