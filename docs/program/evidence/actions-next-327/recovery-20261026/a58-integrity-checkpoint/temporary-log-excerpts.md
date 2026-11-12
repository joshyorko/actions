# Compact verification excerpts from `/tmp/327-*` and the 234-request auth probe

These local results come from a dirty working tree based on integration HEAD `207300bf`; they do not identify a new exact current commit. Original source paths and SHA-256 values are recorded in `README.md`.

- Filesystem output tests: 24 passed in 0.42s. Supervisor: PASS, command exit 0, no remaining owned processes, 9.73s.
- Candidate diagnostic tests: 19 passed in 0.30s. Supervisor: PASS, command exit 0, no remaining owned processes, 5.99s.
- Auth affected suite: 88 passed in 28.46s. Supervisor: PASS, command exit 0, no remaining owned processes, 39.19s.
- Separate configured-key matrix: the retained test covers 58 default and 59 shutdown-enabled method identities, each with missing and wrong bearer requests (234 requests total). The both-modes RCC output reports 2 passed in 6.50s; supervisor PASS, exit 0, no remaining owned processes.
- Historical failing evidence remains in the campaign receipts where named; this excerpt does not replace or relabel any failure.
