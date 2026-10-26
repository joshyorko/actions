# Source-read content revalidation

Hosted Ubuntu source-read mutation assertions failed. The native local47-test
contract passed because timestamp changes happened to expose the writes.
Controlled timestamp observations reproduced the gap without weakening inode,
mode, size, link or name identity. New regression first failed2/passed1, proving
stale inventory returned after exact same-size live byte changes.

Runtimea56 keeps no-follow descriptor/name/metadata checks and rereads selected
content through the same bounded reader during final revalidation, comparing
SHA256 with the matching inventory. New plus existing contracts passed50tests.
No global-atomic snapshot claim; hosted runner timestamp behavior remains
unmeasured. This fixes the local byte-integrity gap without relying on that
environment explanation. Compressed logs preserve original bytes losslessly.
Upstream disposition:none; local reader defect.
