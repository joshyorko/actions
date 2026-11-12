Target: docs/skills/repository-operations.md, source qualification guidance.

When tests run from a dirty checkout, a recorded HEAD commit and HEAD tree identify only the base. Record exact selected test inventories and per-file source hashes, distinguish execution-time hashes from a later checkpoint snapshot, and retain failed attempts alongside corrected receipts. Do not describe the base tree as the tested immutable source. Repeat subset runs and helper runs overlap; report each inventory without adding their pass counts into a unique campaign total. Installed qualification must pin the subsequently committed candidate independently.

Verified basis: source-joined runner captures git HEAD/tree while root source is dirty; selected module hashes and final checkpoint file hashes have different capture times. This addition prevents false immutable-source attribution without discarding historical evidence.
