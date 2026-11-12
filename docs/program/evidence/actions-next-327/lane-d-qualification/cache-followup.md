# Follow-up: cache failure attribution and repeat wheel build

This corrects the unresolved attribution in the first qualification receipt,
without deleting its failed command or log. No source/build configuration changed.

The verbose repetition of the failed command received HTTP 200 repeatedly from
`https://pypi.org/simple/poetry-core/`, then reported:

```
All attempts to connect to pypi.org failed.
("Connection broken: OSError(30, 'Read-only file system')", OSError(30, 'Read-only file system'))
```

It also explicitly reported virtualenv's default
`/home/agent/.cache/virtualenv` as read-only. This is a filesystem/cache failure,
not evidence of DNS loss or an unreachable PyPI server. The first build's success
does not establish that its default cache location was writable. The earlier
README statement that all commands used task-local Poetry caches was too broad:
Doctor/Bootstrap used the declared caches, but the two initial wheel commands
omitted cache overrides. Both exact command histories and failures are retained.

In the already prepared RCC 18.19.3 toolchain, from `action_server`:

```bash
POETRY_CACHE_DIR=/workspace/lane-d/cache/poetry \
XDG_CACHE_HOME=/workspace/lane-d/cache \
poetry -vvv build -f wheel -o /workspace/lane-d/wheels-owned-cache
```

This supported configuration succeeded without filesystem escalation, network
changes, credential changes, or host dependency installation. `poetry` was the
2.1.1 executable from the RCC toolchain, and it used the existing package-local
`.venv`. The verbose log records the owned virtualenv app-data directory.

Both independently invoked builds produced
`actions_runtime-1.1.0a38-cp312-cp312-linux_x86_64.whl`, SHA256:

`34f5b7c1db29d4def4ba84214d225f6b82d037fa39e3b819eab6fe1ff15898ce`

Thus repeat-build equality passes for this checkout, Linux toolchain and current
resolved build dependencies. This is not fresh-cache, cross-host or cross-native
reproducibility: `build-system.requires` currently contains unpinned `poetry-core`
and `setuptools`, and the downloaded RCC input was retained in the checkout.
No native image, SBOM, full Runtime, Windows/macOS or live publisher claim follows.

## Exact ownership request; no edit applied

Request only `devutils/tests/test_actions_runtime_release_line.py`, function
`test_runtime_distribution_and_embedded_rcc_identity_are_explicit`, lines 51–52.
For the current a38 candidate, change the two stale `1.1.0a18` literals to
`1.1.0a38`. Preserve the exact public 1.0.4 canary and RCC 18.19.3 assertions.
This is the smallest correction to the independently reproduced Linux primary
and N-1 toolkit failure (full local devutils result: 275 pass, one failure).
It changes no production/version metadata and weakens no gate. If the integrator
advances candidate identity, it owns selecting the corresponding reviewed value.
After allocation, run the focused test and full devutils suite through package
Poetry. Rollback is a two-line revert. No workflow/config ownership is needed.

## Additional exact canonical-guide delta for integrator

Append under repository operations' toolchain troubleshooting guidance:

> When Poetry reports that all attempts to connect failed, retain a `-vvv`
> diagnostic before attributing the failure to networking. HTTP 200 followed by
> `OSError(30, 'Read-only file system')` indicates a local filesystem failure.
> Set `POETRY_CACHE_DIR` and `XDG_CACHE_HOME` to task-owned writable directories
> for package commands as well as bootstrap; do not change HOME, install host
> dependencies or relax network/security policy. Repeat the failed gate and keep
> both receipts. Matching repeated wheel hashes qualify only the measured
> toolchain/input scope, not untested platforms or globally reproducible builds.

Evidence: retained verbose failure/success logs and matching wheel digests.
Removed ambiguity: connectivity headline alone identifies network failure;
bootstrap cache variables automatically persist into later shell invocations.
Uncertainty: precise low-level cache write that triggered the wrapped request
exception, behavior in newer Poetry releases, and cross-host build determinism.

## Upstream disposition

Candidate: python-poetry/poetry, consumed Poetry 2.1.1. Its installed
`poetry/utils/authenticator.py` catches both `ConnectionError` and `OSError`, then
emits the connectivity headline after retry exhaustion. This establishes a
misleading diagnostic in the consumed stack, not an Actions networking defect.
A minimal draft is retained below; no upstream issue or comment was sent.
Deduplication and current supported-version reproduction are not yet performed;
do not publish the draft without them and target-specific authorization.
Mitigation is supported task-local cache configuration, not an upstream patch.

Draft title: "Poetry 2.1.1 reports connectivity failure after HTTP 200 and read-only-cache OSError"
Expected: distinguish a local read-only filesystem/cache error from failure to
connect. Observed: repeated successful HTTP 200 responses, wrapped OSError 30,
then connectivity-only probable causes. Diagnostic source: installed 2.1.1
`Authenticator.request` catch/retry block. Reproduction: pinned RCC toolchain,
Poetry wheel build in a sandbox with read-only home caches; succeeds with owned
Poetry/XDG caches. Remaining work: identify exact failing cache path, deduplicate,
and reproduce on a currently supported Poetry release. No credential material
or external writes are required for the local observation.

The repeated wheel was also installed into a second absent, task-owned venv by
`qualify_installed_restore_327.py`; the actual installed-helper byte check,
SQLite attachment relocation, original-source preservation and tamper refusal
all passed again. See `installed-repeat-receipt.json` and
`installed-repeat-probe.json`. The original failed build remains preserved.
