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
