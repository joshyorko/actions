# Synthetic invoice reconciliation

Version 0.2.0 is a Linux-local experiment using Actions Runtime **1.1.0a5**,
Work Items **0.5.0a1**, Python **3.12.15** and RCC **18.19.3**. These candidate
packages are not assumed to exist on PyPI. The engine remains in Actions; this
example composes its existing SQL, Canvas/MCP, review, worker and artifact APIs.
It contains no credentials or real business records. Apache-2.0 applies.

From the Actions checkout, use the pinned developer gateway:

```bash
./devutils/bin/develop.sh Doctor
./devutils/bin/develop.sh Bootstrap
./devutils/bin/develop.sh ToolkitTest
ACTIONS_INVOICE_DEMO_DIR=/absolute/fresh/owned/invoice-demo \
  ./devutils/bin/develop.sh InvoiceReconciliationDemo
```

Open the printed `http://127.0.0.1:8765` URL in a local browser. Set
`ACTIONS_INVOICE_DEMO_PORT=0` to select a free loopback port. The task builds the
locked Canvas resource and local SDK wheel, then prepares a task-owned RCC
artifact. An explicitly verified SDK-only fixture may instead be supplied with
`ACTIONS_INVOICE_WORKER_RUNTIME=/absolute/owned/worker-runtime.json`; its SDK hash
must match the selected wheel. This avoids rebuilding an already measured RCC
environment. No existing service, tunnel or identity is changed.

The four invoices total 30,600 cents: INV-1001 matches PO-2001/LED-3001;
INV-1002 has price and PO-total differences; INV-1003 has quantity, PO-total and
ledger-total differences; INV-1004 has line-total, PO-total and ledger-total
differences. The table shows source IDs and expected/actual values. Click
**Review these results**, then **Approve**. Approval creates one fenced
Work Item. Click the host's **Run approved reconciliation** button to execute the
fixed task through actual RCC. Download the scoped result to inspect the distinct
Run and Attempt, claim/source lineage, and one matched/three discrepant records.
Opening the app and offering review never approve or execute work.

Ctrl-C stops the controller. Relaunch the same command with the same directory
and unchanged bytes to recover the same SQL state. Repeated Run delivery returns
the same completed Run. **Reconcile retained execution** is an explicit recovery
action; uncertain execution stays blocked. Changing source, renderer or fixture
bytes requires a fresh directory; retain the old state for audit. The example
does not post to a ledger or promise exactly-once external effects.

The host is loopback-only, with a synthetic server-held actor, ephemeral cookie,
same-origin checks and CSRF protection. This is interactive **E2**, not an
authenticated ChatGPT MCP App **E1**. Working Executor read/write actions do not
by themselves qualify invoice resource rendering, app-audience grants, review,
artifact readback or reconnect in ChatGPT. Do not overwrite an existing tunnel.
Persistent identity, access or tunnel changes require separate approval.

## Smoke and recovery QA

With the controller running, use the prepared Node toolchain from
`action_server/frontend`:

```bash
node scripts/capture-invoice-reconciliation.mjs \
  --url http://127.0.0.1:8765 --out /absolute/fresh/owned/capture
```

This opens the real page, approves explicitly, executes RCC and downloads the
actual scoped JSON. It retains screenshots and a receipt. It does not intercept
MCP responses. Repeat with `--resume` after restarting to assert unchanged
Run/Attempt counts. From `action_server`, with the prepared package environment:

```bash
poetry run python examples/invoice_reconciliation/verify.py \
  --state /absolute/owned/invoice-demo --url http://127.0.0.1:8765 \
  --out /absolute/owned/negative-receipt.json
```

The probe verifies anonymous/foreign-origin denial, persisted actor revocation,
inactive-revision artifact denial, activation rollback, cross-workspace denial
and unchanged admitted work/audit. It temporarily changes only this owned
synthetic fixture and restores grants/activation in `finally` blocks.

The new reconciliation data profile is DuckDB-only. Existing invoice query and
worker acceptance separately exercises real PostgreSQL and both SQL authorities.
This example does not extend the secure filesystem output provider to Windows
or macOS. Full release, generic effect reconciliation, restore/retention and
ChatGPT E1 remain separate gates.

## Isolated export boundary

`export.py` stages only this example, its CSV fixtures, a supplied matching Canvas
HTML resource, and explicitly supplied local candidate Runtime/SDK wheels. It
does not copy engine source or install/publish packages. The manifest records
the source SHA and every file hash. Run it from a committed Actions checkout:

```bash
python action_server/examples/invoice_reconciliation/export.py \
  --output /absolute/fresh/owned/export \
  --runtime-wheel /absolute/owned/actions_runtime-1.1.0a5-cp312-cp312-linux_x86_64.whl \
  --sdk-wheel /absolute/owned/actions_work_items-0.5.0a1-py3-none-any.whl \
  --canvas /absolute/owned/canvas.html
```

In an already prepared **noneditable** candidate consumer with locked provider
dependencies and pinned RCC, launch the exported example with local inputs:

```bash
ACTIONS_INVOICE_SDK_WHEEL=/absolute/owned/export/wheels/actions_work_items-0.5.0a1-py3-none-any.whl \
ACTIONS_INVOICE_CANVAS_RESOURCE=/absolute/owned/export/canvas.html \
  python /absolute/owned/export/demo.py --state /absolute/fresh/owned/demo --port 8765
```

This is a staged candidate bundle, not a public template release or a cold-install
support claim. Repository/visibility and eventual catalog destination remain
undecided; no robot-templates change is part of this export. Preserve the source
manifest, installed-wheel provenance and QA receipts when qualifying a bundle.

After stopping the controller and retrieving evidence, cleanup means removing
only your chosen demo/export/capture directories. They contain the coordinated
SQL database, generated revisions, objects and RCC journals. Do not remove one
part while retaining the others as a recoverable backup. No production restore
or database downgrade is established by this experiment.

## Fresh consumer and retained offline replay

Export version 0.2.0 includes `prepare.py`, dependency constraints generated from
Actions' Poetry lock, verified public Core/Helper floor pins, and allowed wheel
hashes. Use Linux x86_64 with Python **3.12.15** from the pinned RCC gateway.
A fresh consumer uses no existing project environment and imports Runtime/SDK
only from its new prefix. Its first preparation downloads the pinned binary
wheel closure from PyPI with pip caches disabled, verifies artifact hashes, and
installs exclusively from that measured local wheelhouse. Existing proxy/TLS
settings are preserved. No credentials are required by this synthetic example.

```bash
python /absolute/owned/export/prepare.py --root /absolute/fresh/owned/consumer
python /absolute/owned/export/prepare.py --root /absolute/owned/consumer --launch
```

The first launch creates a **fresh** RCC home and SDK-only Artifact. It needs
access to the configured conda-forge and PyPI endpoints, disk headroom and the
native libraries required by RCC's platform compatibility receipt. The Runtime
wheel carries RCC18.19.3. No Poetry, Node, source checkout or pre-existing Runtime
installation is required inside the consumer. Browser automation additionally
needs the prepared Actions Node20.19.3/Chromium QA environment; ordinary browser
use does not.

A second empty consumer can install the identical closure without an index:

```bash
python /absolute/owned/export/prepare.py --root /absolute/fresh/owned/offline-consumer \
  --offline-wheelhouse /absolute/owned/consumer/wheelhouse
```

This proves offline **package installation**. It does not populate a new RCC
Artifact store. Restarting the original consumer with its retained verified
Artifact is a separate replay gate. Keep that distinction in receipts: a warm
RCC home is not a cold or air-gapped host installation. Retain `consumer.json`,
`identity.json`, install report, wheelhouse hashes and RCC verification/journals.
Any source, renderer or wheel drift fails closed. Stop with Ctrl-C, retrieve the
coordinated evidence, then remove only the chosen owned consumer directory.
