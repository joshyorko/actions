# Actions Runtime 1.0.4 owner publish inputs

PR #325 merged as `0e80d41c6b4e5df9579675731e6cdbda733acd35`.
[Production validation 39016104442](https://github.com/joshyorko/actions/actions/runs/39016104442)
passed on that controller: `validate` succeeded, `publish` skipped, Actions/Contents read.
All five post-merge push workflows and all 17 jobs passed. Protected preparation/artifact and both backups remain unchanged. No publication occurred.

Josh can use [Publish Actions Runtime Release](https://github.com/joshyorko/actions/actions/workflows/runtime-release-publish.yml),
verified active with HTTP 200. Select branch `community` while signed in as `joshyorko`.
Keep these original release identities:

```yaml
operation: publish
preparation_run_id: "38951733318"
source_sha: d222f94edca26953c1506ab258adc458ded17c56
expected_version: "1.0.4"
manifest_sha256: 1a77f6c8e09869d6bd45df1b14e6a9ce3f908bcf09351b76cee26a209504878a
```

The workflow uses the current community controller and the original retained release
bytes. Publication remains Josh's action and will reconcile actual remote ownership
and existing file digests again. The two owner backup pairs expire January 14, 2027;
retain/renew exact-byte recovery copies before expiry. Never rerun the protected preparation.
