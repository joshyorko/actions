# RCC task-script descriptor probe, 2026-11-03

An explicitly passed pipe descriptor survived the pinned RCC v18.19.3
`task script -r /workspace/actions/developer/toolkit.yaml -- python ...`
gateway on this Linux executor. The child wrote the exact 31-byte marker; RCC
exited 0, and the outer pidfd/subreaper supervisor reported PASS and no owned
processes remaining. The measured minimum free space was 11,415,191,552 bytes,
above the existing 10 GiB floor plus 48 MiB guard.

The command used a new temporary HOME/ACTIONS_HOME/TMPDIR and the previously
used `/workspace/actions-cloud/robocorp` gateway. RCC materialized a new
`holotree/6fadf84_5a1fac3_9fcd2534` environment (about 914 MiB); it has not
been deleted. This probe does not establish production `env exec` descriptor
forwarding, same-user process isolation, Windows behavior, SDK transport
installation, or a working Action-to-Robot child Run.

The runner, complete log, and supervisor receipt are retained in Library
`libfile_2c0d1374fd9c8191ba68c0965a7883bd` version 0, archive SHA-256
`f6cdb8784e7a11e7ad22799f0656a550b91dad31eb962883d78445369562fa54`.
The runner SHA-256 is
`65f8301ccb1d939a739ae7dda904db46e2e6ba8d0147bff58815db0d353a9ebb`.

A separate focused combined source check ran at local
`79e9a5cf44878e8a05e29cdf1edb813887025653`: capability publication,
internal delegation schema/authorization and policy, and child-admission tests
reported **48 passed, 12 skipped**. Its only difference from the pushed PR head
`78fb182359cbd4d681bf1b69257ef147526ae6b5` is this documentation file, so
executable source bytes match. It uses SQLite and synthetic compiler/Robot
preparation; PostgreSQL and installed child execution are unverified. The
supervisor reported no owned processes. Runner, log and receipt are Library
`libfile_e1b030c801d08191b5ad83fda109bd6d` version 0, SHA-256
`33857bec3049ff95b184a90df36d501d4ac73405132203fec218929610d21f80`.
