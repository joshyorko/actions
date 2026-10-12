Proposed addition to docs/skills/repository-operations.md beside native cleanup evidence:

Retaining an existing thread object does not establish that production joined it.
An observation-only join must use the original remaining cleanup deadline and
record its before and after alive states separately from the original cleanup
return or exception. A successful observer join cannot clear a failed original
cleanup result. Retain module-local constructor observations without adding a
reader or changing its target, arguments, streams or start behavior. ECHILD
records a child-reap observation; pair it with an uncapped final owned census
and the captured pid/create-time identities. Missing identity, reader or census
facts remain unknown, including on timeout and exception paths.
