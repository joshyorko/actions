Documentation improvement:
- Canonical file proposed: docs/skills/repository-operations.md
- Exact addition, after the new paragraph ending “production fallback and timeout contracts stay intact.”:

Audit all fake `waitpid` namespaces, including timeout, raw-error, and rejected
attachment paths. Keep the OS replacement local to the imported harness so its
constants and mocked operations cannot alter unrelated tests.

- Durable learning captured: a portable Linux control needs complete primitive coverage across all error paths, and isolated OS doubles avoid process-wide side effects.
- Evidence: all five immutable0546 fake waitpid sites use _linux_wait_os; every prior assertion preserved; priorfe missing-WNOHANG2RED versus corrected39GREEN under a harness-local missing-constant OS double with failing real process-lifecycle sentinels.
- Stale or ambiguous guidance removed: the new nine canonical lines already correct copying host os fields and frozen-clock fallback behavior. The addition makes the full namespace audit and isolation requirement explicit.
- Remaining uncertainty: simulated missing-constant Linux controls are not an actual corrected Windows runtime result. Exact0546 required CI remains pending; native/controller and lease admission stay unqualified.
Upstream disposition: none.
