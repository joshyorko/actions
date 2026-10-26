# Fresh executor recovery and joined source qualification

The owner-approved recovery commit is
`332e0bd4a9fb8ee06652c63d7f2c11b3b423150b`, parent
`d11650c4e73a0776e75e0ce3dcf1e197eca76b97`, exact saved tree
`9f107225a76f96f6306e0c2b06c94e337a72b36a`. GitHub creation and the
expected-head, non-force branch update succeeded; a fresh fetch verified all
three identities. This saved unfinished work, not an installed a38 release.

On that unchanged source, pinned RCC18.19.3 Doctor and Bootstrap passed;
ToolkitTest passed189 cases. The eight remaining joined modules passed239 tests,
zero skips/failures/errors, with eight explicitly deselected actual-RCC cases.
`receipt.json` identifies every module command, exact deselection, XML, selected
node inventory, source/tree and minimum disk measurements. These are source and
service proofs with owned PostgreSQL/SQLite and real TLS PostgreSQL where the
module uses it. They are not actual generated RCC, installed binary, browser,
authenticated client or full release acceptance. Earlier failed/interrupted
receipts remain unchanged; this continuation does not relabel them.

The standalone controller started one ephemeral loopback PostgreSQL fixture from
the pinned image, required configured service fixtures, ran modules serially and
stopped its container successfully. Modules own their nested TLS fixtures. Raw
logs and private fixture state remain under the exact paths in the receipt; no
private database, TLS key or generated authorization is copied here. The guarded
pytest entrypoint prevents multiprocessing import-time reexecution. The
controller enforced5GiB initial headroom,2GiB running floor,20MiB log and20minute
per-module limits. The canonical disk-budget script also passed during the run;
it was not the initial preflight and is not represented as such.

To reproduce on this prepared cloud environment, copy the two retained Python
scripts to `/workspace/actions-327-recovery-evidence`, source
`/workspace/actions-cloud/activate.sh`, and run `python3 run-joined.py` there with
the checkout at the recorded source. Use a fresh evidence directory: existing
module receipts are deliberately not overwritten. This environment's package
launcher delegates to the committed `developer/toolkit.py`; no host dependency
installation is substituted for RCC/Poetry.

Next: actual canonical two-Action execution and installed version qualification;
review/integrate the retained Knowledge patches and qualify PostgreSQL before
durable ingestion/search. Full original matrix, Robot/direct plans, client,
restore, security and distribution gates remain open. Celld and authenticated
ChatGPT/Dakota retain their separate owner gates. No merge or publication.

Upstream disposition: none.
