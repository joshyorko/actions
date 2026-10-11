# Bounded OAuth build-source admission proposal

READ-ONLY proposal. Existing one-wheel Linux cp312 consumer GO is retained;
OAuth/generated-content and full release qualification remain HOLD.

## Verified cause and recovery state

`action_server/tasks.py::build_oauth2_config` captures two `gh api` stdout values,
ignores both return codes, and writes them directly to `_oauth2_config.py`.
Mocked nonzero empty retrieval produces the exact retained wheel module hash
`f79d95697f1b20691cfff74faa422dc5fa9a13e7fd5d16e98bac3572c6dd7dbe`.
Nonempty error stdout is also embedded. No real acquisition was run by the probe.

The retained 92498 native module hash `4bddd9086d001ed9c86e47faa2bbd89c861ccdaaf09612515dba069c018c5533`
contains two 127-byte API error objects, each SHA `e45906ce02e79f16fb87a838d86bb4e497e37a9591f97608fa013bbcd8b9cbc2`.
They parse as mappings but lack `oauth2Config`. Neither artifact is a recovery
source for valid provider settings. Available Git objects contain no tracked
`actions-oauth-config.yaml`, `oauth-config.yaml`, or generated module.

Current code's only acquisition authority is the unpinned
`Sema4AI/oauth-public-configs` default branch with paths
`actions-oauth-config.yaml` and `oauth-config.yaml`. The connection's repository
metadata lookup returns 404. Parent reports a separate joshyorko repository probe
also returned 404. Neither resolves private/missing/retired status or authorizes a
new owner/repository. Unused task-local path variables do not implement recovery
from local files. Existing development documentation supplies a schema example,
not an approved release source pair or working shared OAuth application.

## Smallest dependency-ready implementation

1. On the existing PR307 branch, first preserve its reviewed changelog change and
   refresh normally onto the accepted target. Do not create replacement infrastructure.
2. Add a small tested acquisition/admission helper used by the existing Invoke
   task. Stop on the first nonzero command, timeout, missing executable/file,
   decoding error, empty/whitespace body, malformed YAML or wrong schema. Validate
   both inputs before replacing the module; preserve the old destination and
   primary error on failure, clean only task-owned temporary files. Capture
   subprocess stderr privately; public diagnostics identify input and failure
   class/exit code without raw bodies, credentials or environment dumps.
3. Require an owner-reviewed input manifest selecting exactly two paths from one
   immutable approved source revision and their SHA-256 values. Verify the raw
   bytes before parsing and retain them unchanged in the generated strings.
   Do not substitute a guessed community repository or mutable default branch.
4. Make acquisition mode explicit in each producer. Release/tag builds use the
   approved remote source pair with credentials scoped as today. PR/source
   canaries use an explicitly supplied, verified local copy of the same approved
   source pair without PAT or remote fallback. When unavailable, source-only
   contract tests remain runnable; OAuth-dependent wheel/native artifact
   production remains HOLD/fails visibly. No successful empty/stub provider
   payload or blind skip is introduced. A future intentionally OAuth-disabled
   canary contract is a separate owner decision, not this recovery design.
5. Emit only provenance metadata after success: mode, source repository/revision,
   input path/digest pair, producer identity and generated-module digest. Require
   post-packaging comparison of the actual wheel/native member to that receipt
   before release admission. Canary/source-only status cannot pass publisher
   admission. Do not change the existing seven-artifact inventory merely to
   carry a receipt; keep it as separate build evidence.
6. Recovery runs old target tasks from `release-source`. Admit the generated
   module through current merged recovery code before native packaging, binding
   it to the approved source manifest. If the old task cannot acquire that source
   correctly, hold that recovery target until a separately reviewed current
   helper invocation targeting the immutable source layout is approved. Do not
   relabel an older task invocation as running the corrected task.

The ready source task is failure handling/structural admission and explicit mode
selection. Actual release-source acquisition remains blocked on the authoritative
pair, pin, authorized source ownership and supported provider contract.

## Schema boundary and tests before behavior changes

Both files must be nonempty strict UTF-8 YAML mappings with mapping
`oauth2Config` and `providers`. Reject YAML null/scalar/list values and API error
objects even when process exit is zero. Provider names/settings and optional
fields must match the existing reader's types. Default-user selected providers
require `mode` actions/custom; resolved selected settings require clientId and
authorization/token endpoints. Do not invent a provider allowlist or require
clientSecret (the consumer supports PKCE). Whether an intentionally disabled
provider map is a valid release policy requires source-owner confirmation;
reject unqualified/empty release content until that policy is explicit.

Meaningful RED/GREEN cases:
- First/second retrieval failure, including nonzero with otherwise parseable
  stdout, empty successful stdout, timeout and invalid UTF-8. A failed first
  retrieval does not call the second. A failed second does not alter destination.
- Empty/whitespace, malformed YAML, null/scalar/list, API-error mapping, missing
  or wrong-typed oauth2Config/providers, malformed provider record, duplicate
  keys if supported YAML acceptance is tightened, and mismatched pinned digest.
- Valid approved source fixture accepted byte-for-byte, without network fallback;
  only source identity/digests are logged. Reuse existing documented/test schema
  for service-free fixtures; never treat synthetic fixtures as release source.
- Atomic write/cleanup failures preserve the primary acquisition/validation
  error and prior file; successful generation's member digest matches receipt.
- PR mode does not invoke gh or receive PAT; release mode cannot admit canary
  scope/missing pins or an API error payload. Poison tests require a valid baseline.
- Exact generator/event/secret conditions and unchanged unrelated AST/output
  parity. Recovery guard demonstrably rejects old empty and API-error modules.
- Package-source CLI tests exercise schema behavior, not merely exit zero;
  installed-member verification remains separate from payload admission.

## Ownership and producer impact

Existing PR307: branch `fix/runtime-release-changelog-selection-20261010`, head
`729594fc04758502ec2ed985adb428e2863a3bb1`, tree
`1db860bf248e83aeedf521044633bbd221902282`, target
`integration/community-release-20261008`. Its tasks/consumer blobs equal current
ba85/PR311; no isolated PR307 checkout exists yet.

Proposed source scope: `action_server/tasks.py`, one acquisition/admission helper
if needed, its focused build-system tests, relevant developer workflow contract
tests, `.github/workflows/_gen_workflows.py` OAuth methods only, and canonical
operations guide. Generated outputs requiring changes/review:
`actions_runtime_tests.yml`, `actions_runtime_pypi_release.yml` (wheel and sdist),
`actions_runtime_binary_release.yml`, `actions_runtime_recovery.yml`.
Other four generated workflow outputs must remain byte-identical.

Manual producers also call the same task: `frontend-build-unauthenticated.yml`
and `action_server_build_cdn.yml`, using repository GITHUB_TOKEN. Update/review
their source mode explicitly; that token is not proof of access to another repo.
Documented local Invoke generation is another producer entry point.

Downstream inputs: generated module included explicitly by Poetry; six cp312/
cp313 platform wheels plus sdist; three native platform builds and Go-wrapper
embedded assets/full package inventories; recovery rebuilds. The generated
module's presence, importability or inventory digest alone admits neither its
contents nor its acquisition source. No retained historical artifact is rebuilt
or relabeled by this proposal.

## Documentation improvement

- Canonical file proposed: `docs/skills/repository-operations.md`, exact patch
  `canonical-guide-proposed.patch`; no repository edits in this lane.
- Durable learning: raw acquisition stdout is not configuration; installed-member
  equality, nonempty YAML and credential separation are distinct admissions.
- Evidence: original wheel review, immutable task mock reproducing exact empty
  module, retained native error-object shape, four generated/two manual callers,
  original-authority 404 and recovery execution layout.
- Stale ambiguity removed: PR OAuth generation described as equivalent despite
  missing credentials and unchecked subprocess failure.
- Remaining uncertainty: approved source pair/owner/revision, availability and
  supported enabled/disabled provider policy; no actual OAuth/release execution.

Upstream disposition: none. Actions owns the ignored return code and payload
admission gap; no provider defect or replacement-repository authority established.
