# Fresh combined a39 installed Canvas acceptance

PASS on source a5eaa1cb0be6dcde2d509f2babbb486d9195ccc1 using unmodified installed
Runtime1.1.0a39/Core1.1.0a4 and fresh synthetic local authorization/datadir.
No monkeypatch, private credential copy, SQL authority seeding or state reset.

Sequential commands actually run (each exit0):

```sh
timeout 1200 /workspace/actions-327-a39/installed-combined/consumer/bin/python -I /workspace/actions-327-a39/clean-e2e/client/qualify.py > /workspace/actions-327-a39/clean-e2e/client/driver.log 2>&1
timeout 1200 /workspace/actions-327-a39/installed-combined/consumer/bin/python -I /workspace/actions-327-a39/clean-e2e/browser/qualify.py > /workspace/actions-327-a39/clean-e2e/browser/driver.log 2>&1
```

Client: blank Canvas public create/apply/build/import/test/activate; one Package
with two generated Actions; two actual detached Tasks plus two app-bound RCC
executions; authorized artifacts; same-state restart and exact Run/Attempt replay;
rollback/restore using rollbackTo; stale AppSession rejected and fresh session
reauthorized retained artifacts.

Browser: second independent blank Canvas public create/apply/build/import/test/
activate, exact-deployment authorization through public CLI, actual reference
host controls mounted/clicked, real RCC word counter returns3. Screenshot
word-counter-artifact.png explicitly shows the authorized result3. Wide/narrow
screenshots retained. Runtime then restarts with the same datadir/profile and a
fresh AppSession reads the same Run/outputs/artifact3. Before/after restart counts
are identical; browser added one Run/Attempt, totaltwo immutable Packages.

Exact wheel hashes: Runtime f023a767234ee5a93fd50281b1ae574b1056893468e13c23bb9d22704a4a6902;
Core fe8fb01f5924837ebd221bb559cc4c36482a581921f81beba1d4c2a6c8e4b371;
Work Items72ef55fc0a7f766fb5d7e4925f8c15bb8211e781b598096ebe9617e1ecad9feb.
Compiler artifactff881cb7903461ed387ab79912105aa0726e91354f8a05b01fd4f337620141d2,
Core53-member wheel proof was independently completed before this serial run.

Both phases stopped their Runtime processes cleanly; browser/reference host
closed in finally. Fixture remains<2MiB and retained logs well below12MiB.
5GiB disk floor checked throughout; no concurrent compiler probes/preparation.
MCP client warns app-only tools are absent from model list when reading retained
artifacts; authorized calls succeeded and exact results were asserted. No warning
is treated as hidden failure or omitted from raw logs.

This fresh run supersedes no history: earlier browser-combined public apply
remains FAIL with unknown cause; its diagnostic and continuation are separate.
This fresh candidate compiled/admitted entirely uninstrumented. Official host
ext-apps2.0.3@82221c0c8ce7661efa6771c9d461511b1650495f is not ChatGPT; E1=false.
No fullrelease/ChatGPT/Robot/retry readiness claim. Upstream disposition:none.
