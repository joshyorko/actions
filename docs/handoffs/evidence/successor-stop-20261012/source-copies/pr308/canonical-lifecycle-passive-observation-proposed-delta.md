Canonical target: docs/skills/repository-operations.md, after provider cleanup scope paragraph.

The verified RCC binary help advertises `env lifecycle inspect --artifact ...
--json`, but a command name and help do not prove passive observation. In
[public revision4148c2b7](https://github.com/joshyorko/rcc/blob/4148c2b71705c9d2baf0e88b48d08a79cb7bda0f/environmentlifecycle/admin.go#L79),
`Inspect` invokes reconciliation; the
[reconciler](https://github.com/joshyorko/rcc/blob/4148c2b71705c9d2baf0e88b48d08a79cb7bda0f/environmentlifecycle/reconcile.go#L61)
removes provisional journals and stale lease records. Do not use that operation
as read-only evidence of natural lease release. The shipped7e588 binary embeds
`vcs.modified=true`, so the public revision does not establish its exact source
or lease schema. A passive lease observer needs separately admitted raw record
paths, root/digest/lease identity, no-follow reads, stable bytes, and actual
before/after observations. Help output and terminal process receipts alone do
not provide those facts.
