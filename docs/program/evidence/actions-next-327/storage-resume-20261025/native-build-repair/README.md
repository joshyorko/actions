# Native build and source-test repair checkpoint

The broad a45 Runtime attempt remains FAILED: 5 failures, 771 passes, 13 skips before maxfail stopped collection execution. Do not present this repair as a complete Runtime or native release gate.

PyInstaller's recursive MCP collection imported optional mcp.cli, which raises SystemExit when Typer is absent. Filter exactly mcp.cli and its descendants before recursion; retain all MCP client/server runtime modules. The resulting diagnostic frozen executable and Go wrapper built successfully, but were built from a dirty checkout and are not source-bound qualified artifacts.

Source self-tests now launch Python modules with -P, avoiding a project actions.py shadowing the installed actions namespace. Runtime's declared Python range supports this flag. The generated public OAuth catalog must be produced through its canonical build task; ignore its current owned path rather than committing generated configuration.

Focused validation: 76 passed, 1 expensive test_binary_build deselected; includes source Work Items API roundtrip, OAuth and build contract checks. Configured Runtime lint and type checking passed (633 files); the optional Markdown linter was unavailable. This source-mode roundtrip is not a native-artifact result. Earlier separate source roundtrip and CLI OAuth regression checks passed (2 tests). The full package suite, explicit source-bound frozen/Go artifact manifests, and native installed gates remain open.

Immutable a44 host candidate remains separate: source d0c87a38a937cc339e8e661ac453c7a62ed41fa6; Library libfile_b8db0ef755208191bd204e83f0d5a04d; 15,679,946 bytes; SHA256 37ab0cf8bf66132c0112e5b65c7528a1092f4665ac7f7d32a022ec2ee77d18b0. Its browser gate may proceed independently in a supported environment. No sandbox repair or policy change attempted; no approval denial.

Upstream disposition: none. Optional CLI collection and source launch are local integration repairs.
