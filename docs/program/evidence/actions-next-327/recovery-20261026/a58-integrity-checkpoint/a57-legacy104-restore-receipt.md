# Runtime 1.0.4 installed-compatibility recovery gate

## Outcome

The a57 legacy installed-compatibility gate **passed its bounded queue and attachment scenario** after the parent identified that the first subprocess had dropped the inherited standard proxy/CA environment. The corrected attempt passed only those already-present, uncredentialed proxy/CA variables to pip; it used the same canonical `https://pypi.org/simple` index, exact staged wheels, and unchanged historical constraints. No alternate route or credentials were used. The original failed attempt remains preserved below as evidence; its apparent resolver conflict was not genuine because `aiohttp==3.14.3` satisfies Runtime 1.0.4's `aiohttp>=3.13.2,<4.0.0` requirement.

The qualified environment is `proxyretry/legacy-consumer-proxyretry`. It passes `pip check` (`No broken requirements found.`), and the independent verifier confirms Python 3.12.15, 67 installed distributions, and exact source-wheel payloads, METADATA and `direct_url.json` SHA-256 identities for all four target packages. See `proxyretry/legacy-profile.json` and `proxyretry/legacy-verify-supervisor.json`.

The unchanged a26 driver (copy SHA-256 matches source `3e04be60f27029e8cd64171becc518394bfdbac1e663863e2a48b87c0b1c4d9a`) passed under the required host supervisor in 11.25 seconds with no remaining owned processes. Results in `proxyretry/gate/summary.json`: candidate a57 queue/attachment read and restart passed; restored relocated fixture read and restart passed; downgrade from a57 to Runtime 1.0.4/Work Items 0.4.4 was refused by the exact schema-6-versus-schema-5 error, and refusal preserved fixture bytes; pre-upgrade backup rollback read and restart passed; retained snapshot stayed unchanged. Scope is **installed legacy local queue and attachment subset only**; full Runtime restore remains `NOT_QUALIFIED`.

The first pip install attempt log is `pip-install.log`; its exact command, return code, stdout digest and byte count are in `pip-install.json`. That run ended with exit 1 in 33.51 seconds and reported no surviving owned processes (`legacy-install-retry1-supervisor.json`). The final corrected attempt's resolver output is `proxyretry/pip-install.log`; its supervisor reports package installation plus the initial verifier process exit 1. That verifier stopped on a local script bug: it treated wheel directory entries as files. The separate corrected verifier handles directory entries, passes all exact payload checks, and did not reinstall packages. An earlier setup-script error is preserved separately in `legacy-install-supervised.log` and `legacy-install-supervisor.json`.

## Inputs and qualification context

- `../legacy104-inputs/receipt.md` records verified official PyPI wheels for Runtime 1.0.4, Core 1.0.3, HTTP Helper 1.0.3 and Work Items 0.4.4. The Runtime wheel is the exact published Linux CPython 3.12 artifact, SHA-256 `ab0925ddfbc804d4790b5bd839461310b851c3dedf5f4781e4b4c8472bcf5eba`, matching a26's retained `legacy_wheel_sha256`.
- The installed-smoke receipt records Core 1.0.3, while the historical source lock at commit `d222f94…` pins Core 1.0.2 as its develop-path source. This attempt uses the recorded smoke tuple (Core 1.0.3), which satisfies Runtime's published Core range. It would qualify authentic published inputs, not reproduce the older smoke's different Runtime wheel bytes (`a8cb07…`).
- `historical-constraints.txt` is derived from the historical source lock and pins the 69 main-group package identities plus the four target packages. The derivation and source lock digest are in `historical-constraints-receipt.json`; the constraints file digest is `f061895c46b0a1c4d184eb4a582da8a3031f2e8a4caa893ab22ed21cb0658a6d`.
- The failed first attempt used only the four staged verified wheels as direct inputs, `--isolated --no-cache-dir`, the historical constraints file, and `https://pypi.org/simple` for ordinary public dependencies. The child environment had inadvertently omitted the inherited proxy variables. It logged `[Errno 101] Network is unreachable` for `/simple/aiohttp/`, then misleading `ResolutionImpossible` text attributing the failure to `aiohttp==3.14.3`. A local `packaging.specifiers.SpecifierSet('>=3.13.2,<4.0.0')` check returned true for `3.14.3`. The corrected attempt reached the same official index via the inherited standard proxy and installed successfully; see `proxyretry/pip-install.json` and `proxyretry/legacy-profile.json`.
- `prepare_legacy.py`, the corrected `proxyretry/prepare_legacy_proxy_retry.py`, read-only verifier, unchanged a26 driver copy, and their supervised logs are confined to this new probe directory. The incomplete first `legacy-consumer` remains explicitly unqualified. The separate corrected environment and gate are recorded under `proxyretry/`.
- The prepared RCC setup gateway passed Doctor, Bootstrap, and ToolkitTest: 213 checks passed. Its supervised receipt records exit 0, 104.93 seconds, and no remaining owned processes.
- Candidate comparison target remains the separately prepared `/workspace/327-probes/a57-locked-consumer/consumer`; its ready receipt identifies the a57 installed candidate and reports no broken requirements. It was not modified.
- Disk preflight at the start recorded 18,310,479,872 free bytes. No GitHub artifact or run was accessed. No credentials, grants, settings, source checkout, or delivered consumers were changed.
- Post-gate free space is 18,138,882,048 bytes, above the 10 GiB floor. Both supervisors report no surviving processes. The existing a57 consumer and artifacts were not modified.

## Remaining qualification limit

This evidence qualifies the local queue and attachment subset only. A separate Runtime/database restore campaign would be needed for any full restore claim; this gate did not attempt one.

## Canonical documentation improvement

Propose a focused addition to `docs/skills/repository-operations.md` documenting the installed-compatibility recovery gate as a distinct evidence profile: identify the exact published wheel hashes and companion versions; state when a source lock's develop-path identity differs from the installed smoke tuple; require resolver access and installed wheel-payload/hash checks before qualification; and label queue/attachment safe-refusal and rollback results separately from full Runtime/database restore. This is a proposal only; no repository documentation was changed in this probe.

**Upstream issue disposition:** none filed; the bounded scenario passed its defined checks and did not establish an upstream product defect.
