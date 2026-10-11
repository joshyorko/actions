# Additive PR delta provenance correction

The first announced PR-delta JSON/Markdown hashes (`a6a2e587…` and `24bbce7d…`) do not have retained bytes. The files at those paths were overwritten before freezing; a read-only hash search under `/workspace` found no copies. They are marked **ORIGINAL_BYTES_NOT_RETAINED** and have not been reconstructed. The later versions remain unchanged at JSON `0ed464ca…` and Markdown `facced8db…`.

At 00:39 UTC, GitHub PR GET, commit GET, and read-only `git ls-remote` all bound PR311 to `c888fb4a33fb2f8aa2bc30700d36ff92ccf535ca`, tree `34f967cc9b753e8b0497221cf77ec53925cdf9eb`, parent `8eb2e6f92109bcbd51e4925ebe703074ee28c6ac`; the remote branch ref agrees. The PR body still describes the prior 8eb head. Independent source review is GO for c888, and the bounded source-only gate has 38 focused tests, Ruff and Mypy pass. Controlled clean-wheel acceptance remains NOT RUN. An earlier incidental 39-test selection invoked wheel builds and clean installs, then RCC was aborted during Mypy; generated artifacts were deleted and three adopted zombies remained. That incident is not #195 acceptance.

The Windows failure in run `38096394555`, job `114343060346`, tested old head `8eb2e6f9` through synthetic merge `bc38345` into `19380993`; it is not evidence about c888. New-head CI is pending. PR305/#99, PR306/#84 and PR310/#208 close-keyword text is only a conditional future-closure directive. No corresponding closed event was observed. PR221 had zero issue-closing references in the retained scope; GraphQL closing edges remain UNKNOWN.

Canonical documentation delta: none. Existing repository-operations guidance already covers live target-ref checks and exact-head evidence binding. Upstream disposition: none.
