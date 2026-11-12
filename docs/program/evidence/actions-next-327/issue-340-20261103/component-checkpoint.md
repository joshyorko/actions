# Issue 340 component checkpoint

Release PR #328 remains at `642c6d3f62c2d271d33459553ef560a10f283f1f`.
The separate checkpoint branch is an integration work in progress, not another
release or a claim of acceptance.

The explicit Deployment model-publication selection and its four focused tests
are recorded in `eb102217f614f24217d2c58c311c15131d7a6721`, tree
`f8b3e0617221cadbd153348c419a4be00943ad63`. The same test file against the
unchanged 642 source failed four tests because the new field was absent. On the
new source, four tests passed. The first new-source attempt had four fixture
setup errors because the fresh worktree lacked its pinned RCC binary. A symlink
to the already present RCC 18.19.3 executable (SHA-256
`7e588c01751ca2ae15ba13ef67f2f4b7567697a5a8389737059a73936f509428`)
provided the test fixture prerequisite; the setup failure is not reclassified.

The isolated managed Work Items MCP facade and its five focused tests are in
`098bc4eb8dd05b5ddfdd46dc6ac3b3a7c5c0b921`, tree
`48f9c1546de96acfd75357501760d7b693c36ce2`. It has no native startup wiring.
The test passed five cases after four failed attempts: canonical workspace ID
conversion, strict wire-command validation, a missing await, and strict
wire-result validation respectively. Those failures are retained as failures.
The passing check includes a model-publication/grant revocation control and
rejection of review and retry-only request fields. It does not prove real SQL
worker execution, host policy configuration, or transport startup.

Both passing tests ran with RCC `task script -r /workspace/actions/developer/toolkit.yaml`
and the prepared Action Server Python 3.12 environment, using the isolated
worktree source and `pytest -p no:cacheprovider` on the respective test file.
The pre-commit tested product and test bytes are the bytes in the stated commits;
the subsequent committed guide text was not executable input. A host Python
pidfd/subreaper supervisor and 10 GiB floor plus 48 MiB capacity guard supervised
both runs. The passing supervisor receipts report command exit 0 and no remaining
owned processes; minimum free bytes were 13,519,843,328 and 13,514,579,968,
respectively. No aggregate, publication or production deployment was run.

Raw test and supervisor logs remain executor-local under `/tmp/actions340-*`;
they are not durable release artifacts. SHA-256 of the successful publication
log is `fdc4c5cb8de557536ff8bd9b33081de92335a69b5c5d6d95d4c6b83f49af7901`;
the successful managed log is
`86f093a6e376cfd493b87e1780496bd2db09c300603ad41fadcbbac1106b6f29`.
The component results are not installed-release evidence. Discovery, shared
MCP wiring, synchronous and detached model-publication checks, internal
Action-to-Robot invocation and the #340 acceptance matrix remain open.

Upstream disposition: none.
