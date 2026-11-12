# Remaining active defaults and publisher audit

Read-only current source review; no network, credential inspection, external mutation, PG or environment materialization. Prior closed dependency/scaffold/gallery/docs/TLS/logger/publisher fixes are not reopened.

## Focused remaining fixes

1. **Automatic legacy Studio discovery remains active.** actions/src/actions/agent/_client.py:34–54 first tries explicit SEMA4AI_AGENTS_SERVICE_URL, then automatically reads OS-specific Sema4 Studio agent-server.pid (:65–82, :102–130). It trusts base_url from that local file and probes /api/v2/ok via actions_http with invocation-context header (:86–99). Trigger: exported prompt_generate/list_data_frames/get_data_frame construct _AgentAPIClient at actions/agent/__init__.py:253/301/351. This is not a hard-coded vendor cloud hostname, but it is active implicit coupling to the legacy product. Proposed focused fix: require an explicit owner endpoint or explicit PID-file option; preserve SEMA4AI_AGENTS_SERVICE_URL as an explicit compatibility alias, give owned configuration precedence, and stop before file/network access when absent. Tests should prove omitted configuration does not read legacy files, explicit owned endpoint wins, explicit compatibility still works, and failed explicit selection does not silently fall back. Do not change payload semantics or remove legacy input support.

2. **Windows signature embeds vendor branding.** action_server/src/actions/server/_build_common/signing.py:244–246 always passes --description-url https://sema4.ai. Caller chain: tasks.py build_executable --sign -> _build_common/workflows.py:197/238 -> sign_windows_executable. Current .github/workflows/actions_runtime_binary_release.yml:167 invokes signed build when repository-owned signing secrets are configured. This URL is embedded artifact metadata, not a request to the vendor or a credential destination. Proposed narrow fix: owned project description URL or explicit owner-supplied signing metadata, with command-assembly test proving no vendor URL default; preserve signing certificate/timestamp logic, legal attribution, and explicit configuration. No signing or live secrets needed to test.

3. **Work Items release still needs remote vendor source for independent provenance.** .github/workflows/work_items_release.yml:39–45 checks out robocorp/robocorp at631f5601617e9935620a72c788a98e1012331323. Verify job triggers on relevant PRs, community pushes and actions-work-items tags; lines66–70 invoke check_contract_port_provenance.py --robocorp-root plus owned custom-adapter ref. This is a deliberate pinned verification dependency, not package runtime or vendor publishing. Offline digest mode already exists at work-items/scripts/check_contract_port_provenance.py:454–476 but is weaker than authoritative source comparison. If release qualification must be entirely independent of vendor availability, vendor the exact minimal reference fixtures/hashes with licenses or supply an owner-retained immutable reference artifact, preserving independent proof. Do NOT silently replace authoritative comparison with offline digest-only verification. Scope should be separate Work Items owner review.

## Retained non-edge cases

- ActionServerTool/AgentCliTool vendor URLs are guarded retired download metadata; RccTool overrides download to owned GitHub. No new active edge found there.
- _settings.py:225/228 old Robocorp local data directory is a durable storage compatibility path, not external dependency. Changing it without migration would break recovery.
- _args_dispatcher.py:21/220 contains old CLI branding/help link. This is stale product-facing text; low-risk owned-name/link correction is reasonable but does not close a runtime network dependency.
- Original source/issue/license attribution and compatibility env names remain. Do not blanket rename/delete them.
- Explicitly configured Reducto/gallery inputs remain intentional compatibility. No implicit vendor endpoint found in those corrected paths.

## Publisher disposition

No remaining vendor S3/downloads or template publisher workflow found. The current Core/HTTP-helper/Work Items workflows are owned distribution tag publishers gated by verification and pypi environment; runtime-release-publish is explicit operation=publish and owner-actor gated. Runtime signing secrets are explicit repository configuration, not hard-coded vendor credentials. Existing workflows are still live publishing capabilities, but none was invoked or treated as authorized publication here. Prior deleted vendor publisher is not repeated as open work.

Exact next gate: local no-side-effect tests for explicit-only agent discovery plus Windows command metadata tests. Work Items pinned provenance availability remains a separately classified build verification edge with owner decision needed; do not block installed Runtime testing on historical strings.

Documentation improvement:
- Canonical file proposed: docs/skills/repository-operations.md.
- Exact addition: “Dependency/default audits distinguish runtime acquisition, implicit local service discovery, artifact metadata, and pinned provenance verification. Agent PID discovery can couple to a legacy service without a hard-coded cloud URL; signing description URLs affect artifact identity without being network destinations. A pinned reference checkout in a release verify job is a build-time availability dependency and must retain independent provenance assurance if made offline. Historical data directories, explicit aliases and license attribution are not removable dependency edges.”
- Evidence: exact callers, signing workflow condition, Work Items checkout/verification trigger above.
- Stale ambiguity removed: vendor strings are neither all harmless nor all executable upstream dependencies.
- Remaining uncertainty: no real agent service, signing or release workflow executed; remote workflow permissions/settings not inspected.

Upstream disposition: none. Draft-only remediation proposals; no external reports.
