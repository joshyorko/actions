# Joined Robot components, not canonical Robot activation

Base9340bc8aac7a4534b50f27bef522f1a942f20afa plus this checkpoint. Integrates approved C commits bc9896d69a2df05cea5b450aea856f3b808e83ed, 3de78ad4d14963ec2260c2927f66b298b218a377, 7337d9b4e8c8a6e3704b58e74e872a66115ed910 and 133359581e490cb0aa1104de1b97acdc6acbf38f, with independently reviewed replacement journal patch99ed3596195bac9b1c165d51cae6430a1efb62b64022be1e201c929e32dd0c42.

Root component gate: 94 passed, 2 skipped. Adapter30pass/2prepared-RCC-skips; builder15pass; lifecycle7pass; journal42pass split21SQLite/21ownedPostgreSQL. Exact selected inventories and XML retained. The first controller failed after successful adapter tests while hashing an incorrect test-directory path; corrected remaining controller ran the other three modules. Original failure is retained. Owned PostgreSQL cleanup exited zero. Do not count these as installed Robot execution or combine overlapping historical counts.

The original journal's 40-pass suite missed nested transactions: review proved a SAVEPOINT acknowledgement could precede the outer commit and be erased by rollback. Two regressions failed on SQLite/PostgreSQL, then the entry guard rejects existing transactions before mutation. Successful record acknowledgement now follows the journal's own outer commit and live read-back. Reads remain reconciliation-only, never spawn permission. Earlier failures and missing historical receipt logs are preserved in journal/.

Builder VerifiedRobotPackage denotes measured bytes, not trusted admission. Its request permits up to256 files but the shared source snapshot enforces16 files,512KiB each,2MiB aggregate and canonical0644 archive modes. Direct plans contain no fabricated RCC digests. Canonical registry admission and retained identity resolver remain required.

Lifecycle stage performs authority checks before provider I/O; adapter's final live check must remain, and terminal publication needs an atomic fresh-authority fence. Spy tests are not mid-I/O revocation evidence. A real provider barrier/revocation test, competing same-attempt execution, recovery/restart, canonical Work Item wrapper and installed Robot acceptance remain open.

No new scheduling authority, registry registration, admission, terminal publication, retry or startup wiring is claimed by this slice. Upstream disposition:none.
