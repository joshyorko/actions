# Clean installed a38: two Actions, Tasks, App artifacts and rollback

Exact source f332a8284e78844abcf6700a600d2891d742b682. Runtime Linux CPython3.12
wheel SHA256103c53cf3b960fe173d6fa53485e097267a071684bc464214739b660a4c33203.
Core a3 and Work Items0.5.0a2 retain their measured hashes in wheels.json.
Both frontend entrypoints rebuilt from the archived lock; clean noneditable
consumer pip check and isolated import passed. This supersedes the failed
4babd01c wheel for this acceptance, not historical test accounting.

Ordinary loopback installed CLI, genuine MCP2.3 client, owned synthetic scoped
API authorization, and public stopped-local owner authorization completed:

- Blank Canvas -> typed forms plus two generated Python Actions -> real RCC
  compile/import/test -> one immutable Package and explicit Deployment activation.
- Both Actions executed as detached MCP Tasks with acknowledgment, terminal
  result, exact common Run/Attempt/intent/TaskReceipt identity and reconnect replay.
- Both Actions also executed via AppSession-scoped canvas_dispatch. Public
  canvas_artifact returned actual expected values `a b` and `16`, not local
  filesystem or direct SQL result substitutes.
- Restart preserved both terminal Tasks. Historical rollback to the blank
  revision removed invocation descriptors; rollback back restored the exact
  immutable two-Action revision. Fresh AppSession authorization read both retained
  artifacts; the pre-restart AppSession was rejected. No new Run/Attempt was
  created during this continuation.

`client-fixed` retains FAIL: after all four genuine executions and public
artifact reads, its rollback test incorrectly used candidateRevision for a
historical activation. `client-continuation` is PASS using the documented
rollbackTo command against those exact retained Runs; it did not rerun work or
rewrite the failed receipt. Earlier UI discriminator and offline loader failures
remain in installed-initial. Intermediate working polls remain local; initial
acknowledgments, terminal polls, public tool results and exact identities are
retained here. All published JSON was sanitized before writing. Private profiles,
API keys, raw AppSessions, datadir and fixtures are excluded.

Separate gates remain: official rendered host/second app, actual fresh model
client, ordinary Knowledge host/Task/generated consumption, full final matrix,
owner celld and authenticated ChatGPT decisions, distribution/security/restore
breadth. No release-ready, publication or authenticated ChatGPT claim.

Rollback: keep this exact wheel trio and the corresponding coordinated private
snapshot. Schema22 cannot be opened by schema21 readers; restore the matching
older snapshot for candidate downgrade. Public UI rollback changes only the
active immutable Deployment pointer; retained Run pins remain unchanged.

Upstream disposition: none.
