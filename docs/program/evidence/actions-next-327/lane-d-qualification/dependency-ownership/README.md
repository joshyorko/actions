# HTTP/Common ownership audit and concrete migration scope

Actions integration inspected: aa388093dbc6794030e84ff23ec8dbb4ad407fb1.
Extension read-only checkout: joshyorko/vscode-extension at
587aa1afb4c1acbb6e21e0be87b1116fbe8ea51c. No extension edits/pushes or live
installation changes. Private owner log was not copied; only parent-supplied
sanitized dependency/controller facts informed the source search.

| Source | Distribution/import | Actual coverage |
|---|---|---|
| actions-http-helper/src/actions_http | actions-http-helper 1.0.3 / actions_http | Existing wheel/sdist build, http_lib_release.yml, http_helper_tests.yml, Runtime PR candidate-helper wheel build |
| action_server/src/actions/server/_common | No standalone distribution; internal version 0.3.0 / actions.server._common | Included in Runtime wheel/frozen bundle, not an independently released Common artifact |
| common/ | Historical sema4ai-common docs/lock/test conftest only | No pyproject, tasks or source; cannot build standalone Common today |
| Extension create_env descriptors | sema4ai-http-helper 2.1.0; sema4ai-common 0.1.0 | All four OS descriptors plus generic conda.yaml still install vendor names |
| Extension Poetry metadata | sema4ai-http-helper ^2.1.0; sema4ai-common ^0.1.0 | Lock resolves helper 2.1.2/common 0.1.1; dev sema4ai-actions 1.4.1 also reintroduces vendor helper |

Owned helper METADATA requires pyyaml>=5, truststore>=0.10,<1,
types-PyYAML>=6, urllib3>=2.5.0; Python>=3.10,<4. Core wheel requires
owned actions-http-helper>=1,<2, Runtime requires >=1.0.3,<2.
Inspected Core/helper/Work Items wheel metadata does not require vendor Common or
HTTP helper. Existing clean 67-package Runtime inventory likewise has neither.
Generated Runtime action-templates.zip text files have no sema4ai dependency
references. Some source template comments/changelogs retain historical names;
these are not installation requirements and must not be confused with attribution.

Common standalone manifest was deleted in Actions c08e4c4b. Its prior metadata
was sema4ai-common0.3.0, Python^3.11, psutil>=5,<7, owned helper^1, PyYAML^6,
msgspec>=0.18. Existing internal implementation must be reused, not duplicated.
Repository Apache-2.0 license retains Copyright 2024 Sema4.ai, Inc.; preserve this
and vendored module notices during any extraction. The stale internal docstring
is not evidence of a remote service call.

## Exact extension callers and configuration scope

- sema4ai/bin/create_env/{conda.yaml,conda_vscode_linux_amd64.yaml,
  conda_vscode_windows_amd64.yaml,conda_vscode_darwin_amd64.yaml,
  conda_vscode_darwin_arm64.yaml}: vendor distribution pins.
- sema4ai/pyproject.toml lines47–48 and poetry.lock: main dependencies; dev closure
  also needs owned Core substitution where sema4ai-actions pulls vendor helper.
- sema4ai/src/sema4ai_code/data/data_server_connection.py: three sema4ai_http
  imports and post/put calls. Owned actions_http provides the matching APIs;
  call-contract tests are still required before migration acceptance.
- sema4ai/src/sema4ai_code/_lint.py:202: only discovered production Common caller,
  sema4ai.common.run_in_thread.run_in_thread. Existing Runtime internal module
  supplies this API without third-party imports.
- sema4ai/tests/sema4ai_code_tests/data_server_cli_wrapper.py: download helper caller.
- Controller string Sema4aiCode occurs in src/sema4ai_code/rcc.py,
  src/sema4ai_code_debug_adapter/launch_process.py, vscode-client/src/rcc.ts,
  vscode-client/src/clear.ts. Replace controller provenance coherently; retain
  --bundled/--sema4ai until compatibility tests establish required RCC behavior.
- bin/create_env/build_environment.py selects the platform descriptor and contains
  a CDN prebuilt-environment shortcut. Fresh qualification must avoid accepting an
  old vendor-containing prebuilt/warm environment; inspect the consumer bootstrap
  path and generator fingerprint contract together before changing it.

Owner log states RCC18.19.7 and telemetry=false. That does not establish a vendor
service call; controller/user-agent identity and blank endpoint diagnostics are
separate facts. No owner host/user/install identifiers retained here.

## Executed owned-helper qualification

Built existing source in isolated native-20639810/actions-http-helper; relevant
package/Common/template files have no diff between20639810 and aa388093.
Prepared RCC toolchain, package-local Poetry, writable caches:
`poetry install`, `poetry build`, `poetry run pytest --junitxml=...`.
Wheel+sdist PASS; 12 tests PASS. Fresh venv from prepared package Python, offline
pip install of newly built helper wheel with /workspace/lane-d/resolved-wheelhouse;
actual six-distribution inventory (including pip) retained. Import origin is inside
helper-owned-clean; no sema4ai-http-helper/Common; pip check PASS. Cached wheel
bytes were used as install inputs, not a warm installed environment. This does
NOT qualify the extension RCC bootstrap or installed VSIX.

## Smallest migration proposal requiring integrator allocation

Make one canonical owned Common source, proposed distribution actions-common and
namespace actions_common, starting from existing Runtime _common implementation.
Move rather than copy it into common/src/actions_common; migrate Runtime imports
(or narrowly retain compatibility forwarding where needed). Restore Common
pyproject/tasks/tests and package map/build coverage through integrator-owned
metadata/locks/release hooks. Choose initial owned version centrally. Do not make
Common depend on full Runtime merely to satisfy the extension's thread utility.
Then change actual extension HTTP/Common callers, all descriptors, Poetry closure,
controller builders and fresh-environment regression tests coherently.

Exact production/import/package ownership is not yet allocated to this lane;
no unilateral shared source/version/lock edits made. Extension replacement VSIX
build/install proof is pending that package artifact/contract and a supported
extension build environment. No public publication, signing or credentials.

Canonical guide delta proposed: “Audit extension environment descriptors and
actual Python imports separately from Runtime wheel closure. Owned HTTP helper
already builds as actions-http-helper/actions_http; Runtime's internal _common
is not a standalone Common distribution. A fresh VSIX bootstrap must consume
owned helper/Common artifacts and verify installed distribution names/import
origins; warm holotrees or a Runtime-only smoke cannot satisfy that gate.”

Upstream disposition: local owned-repository migration gap, no external report.
Learning/evidence: installed helper receipt, source caller map and removed Common
manifest history. Uncertainty: final Common namespace/version allocation and
extension clean installed acceptance remain pending; no success claimed for them.

## Direct publication/provenance answer

No standalone owned actions-common build/release target at audited integration
SHA; current package map lists Core/Runtime/HTTP Helper/Work Items/devutils only.
PyPI actions-common JSON/project endpoints both returned404 on2026-10-25. This
establishes current absence under that exact name, not absence of every possible
historical alias.

- [Owned distribution build map](https://github.com/joshyorko/actions/blob/aa388093dbc6794030e84ff23ec8dbb4ad407fb1/devutils/src/devutils/invoke_utils.py#L44)
- [Current release workflow directory](https://github.com/joshyorko/actions/tree/aa388093dbc6794030e84ff23ec8dbb4ad407fb1/.github/workflows)
- [Vendor PyPI0.1.0](https://pypi.org/project/sema4ai-common/0.1.0/)
- [Vendor package source](https://github.com/Sema4AI/actions/tree/9d9479e842effbcb56d2ec0017c23593d192a56d/common)
- [Available vendor Common Release workflow](https://github.com/Sema4AI/actions/blob/9d9479e842effbcb56d2ec0017c23593d192a56d/.github/workflows/common_release.yml)

Vendor workflow builds from ./common on sema4ai-common-* tags, runs Poetry install,
check-tag-version, build and publish. Its current workflow is evidence of the
available build path, not cryptographic proof of the0.1.0 upload's exact source
revision. PyPI0.1.0 has no published provenance attestation. Its wheel SHA256 is
46c8e07d1420bf507300a51624e27e0dad1ecc3036604f57513d91d29926a917,
verified against downloaded bytes. Layout and METADATA retained in sanitized
package-provenance.json. License declaration is Apache-2.0; this particular wheel
has no separate LICENSE member. Preserve the source repository license/notices.

Historical sequence is now verified more precisely:
[51a0ffb0](https://github.com/joshyorko/actions/commit/51a0ffb0fb9625a70f5a08af19e199cc11c22385)
moved common/src/sema4ai/common into Runtime _common and removed common_release
and common_tests workflows. Later
[c08e4c4b](https://github.com/joshyorko/actions/commit/c08e4c4b3e1a974b47d81e7e0c9dc83ede63c082)
removed the leftover Common pyproject/tasks. Thus source was absorbed/unpackaged
in fork history, not never included. The extension's exact required
run_in_thread.py is BYTE-IDENTICAL between vendor0.1.0 wheel and current owned
Runtime internal file, including run_in_thread and run_in_thread_asyncio. This
supports reusing that implementation; it does not assert equality of every Common
module or compatibility of all HTTP call sites.
