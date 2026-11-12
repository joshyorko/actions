# a47 installed claimed Robot qualification

PASS on immutable source 06845ba906b86c5329c6f63f9a3ca20cfee16d4c, Runtime a47 wheel SHA256 9ff4d0baa9e7cf4201225ff0323addf1dd9be88588fe27ab85ddfbfd2af17ddc, Core a7 wheel 9e8a1e687bbce5e444f2dfdd5890d30176ab84ae68384b5ef6af9c3e86dcea74 and Work Items a2 wheel 72ef55fc0a7f766fb5d7e4925f8c15bb8211e781b598096ebe9617e1ecad9feb.

Four fresh public runs exercise model invocation and app-associated Canvas submit_input/execute, each with real Robot/RCC success and failure. Exact enqueue replay, claim/fence, terminal queue state, four authorized artifacts per Run, missing/wrong credentials and restart reads passed. Model-only runs intentionally cannot read through canvas_artifact: that surface requires a Canvas Request/Audit association. Associated Canvas runs read through both authorized surfaces. Single Actor/server-held worker only; producer/children, claimed Tasks and multiple principals remain unqualified. No browser acceptance is claimed.

Supervisor exited zero with no live descendants or cleanup errors. The six skipped regression cases and their exact reasons are in regression-summary.json; the owned PostgreSQL was stopped. Original a46 replay failure and a41 lifecycle failure remain failures.

Configured lint/typecheck first FAILED one formatting check in generic_service.py. The only repair wraps the admitted item call across lines; configured lint and typecheck then PASS (642 files). This formatting-only source delta does not mutate the immutable installed a47 wheel. Full applicable Runtime suite is still pending; its prior resource-aborted run is not a pass.
