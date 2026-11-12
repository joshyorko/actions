# Native bundle and source launch review

Result: no blocking defect found in the reviewed fix. Only authorized Python/spec/test files were formatted; no commits, metadata/version edits, installs, DB/RCC materialization or native rebuild by this lane.

Focused source verification:76 passed,1 expensive test_binary_build deselected,0 skipped in5.76s (focused.xml/log). Selection: test_binary.py, test_oauth2.py, test_community_oauth2.py, build-system OAuth config and community OAuth config tests. SEMA4AI_INTEGRATION_TEST_ACTION_SERVER_EXECUTABLE explicitly removed from test environment, so the Work Items roundtrip exercised source Runtime startup from a project containing actions.py, not the frozen binary. No browser/installed-release claim.

Configured Runtime invoke lint PASS (Ruff, configured formatting, isort; optional Markdown linter unavailable). invoke typecheck PASS633 files. Evidence lint.log/typecheck.log. Root's existing diagnostic native build evidence /workspace/recovery327/a45-native-filtered.log reports successful final action-server-diagnostic-a45; it was inspected, not rebuilt here.

## Findings

Original /workspace/recovery327/a45-native-build.log shows collect_submodules('mcp') recursively importing mcp.cli.cli, which tries optional typer and then raises SystemExit1 when absent. This is an overly broad owned bundle scan, not missing MCP runtime dependencies. Actual installed PyInstaller helper applies the supplied filter before putting each subpackage on its recursive import queue. The new filter rejects exactly mcp.cli and its dot-descendants; it preserves mcp.client, mcp.server and all other runtime modules. Existing tests explicitly distinguish mcp.client from the similarly prefixed mcp.cli. No optional Typer installation is required.

Source launch helpers now use Python -P to avoid automatically prepending project cwd for -m actions.server. This prevents a project actions.py from shadowing the installed actions package in the tested default source-launch path. It does not remove caller-supplied PYTHONPATH and is not a sandbox boundary. Native executable/frozen branches are unchanged. Runtime declares Python>=3.12,<3.14, so -P is supported throughout that declared range (it would be incompatible with3.10, which Runtime does not support). Core's separate older Python support does not make _selftest a Core API.

Generated public OAuth module is ignored by action_server/.gitignore line15 (src/actions/server/_oauth2_config.py); no credential content was copied or displayed. Root-reported root .gitignore had no uncommitted diff at inspection; effective nested ignore was verified with git check-ignore.

## Exact canonical guide proposal (root applies)

Target docs/skills/repository-operations.md, native/source verification:

“Freeze MCP runtime modules without recursively importing its optional development CLI. Filter the exact mcp.cli namespace and descendants before collect_submodules recursion; preserve mcp.client and mcp.server, and do not add optional CLI dependencies merely to satisfy an overly broad bundle scan. Source -m Runtime test launches should use -P on supported Python versions and include a project containing actions.py to catch cwd shadowing. Keep source roundtrip results separate from frozen-binary execution. Generated public OAuth configuration belongs to the ignored build output and must not replace an operator's private registration.”

Documentation-improvement receipt: original Typer/SystemExit trace, installed PyInstaller recursion implementation,76 focused source passes, configured static gates and effective OAuth ignore support this delta. Ambiguity removed: optional CLI build-time import versus mandatory Runtime dependency, and source helper cwd protection versus frozen/native qualification. Remaining gate: root owns final source/commit linkage and clean installed/native candidate qualification.

Upstream disposition:none. Owned bundling/test-launch configuration corrections; no confirmed upstream defect, no external mutation or reporting target. External reporting authority remains draft-only.
