# Logical preview follow-up

Apply after frozen logical checkpoint f56f927ecc2aeac9729a86d8ceefcfae66f7b87c6289e0e983c8dc288fd2da48. Separate patch SHA256 da3863ca6749687b5a4f08f2a1c5b0fa795d13ebd6180f6a082732c9ea20608f. Original checkpoint scratch and patch unchanged.

Preview and apply reject any provider reference outside the caller Workspace immediately after syntax parsing, before provider or compiler access. Preview with logical declarations or choices now returns dataBindingValidation: syntax=passed, compatibility=not-checked, readiness=not-checked, and a matching bounded summary. Legacy preview response is unchanged. The existing synthetic forwarding fixture was corrected to use the actual caller Workspace, preserving its replay-fingerprint assertion.

Red: red.xml3failed1passed. Green: green.xml4passed. Joined: joined.xml5passed,44deselected; no provider/RCC calls. Ruff passed; static2.log mypy2explicit files with no incremental cache passed (initial one-file command resolved an older imported declaration and failed; corrected source paths include authoring_values explicitly). No PG proof is claimed for this pure parsing/projection follow-up.

Exact canonical guide addition to Public Data and Knowledge integration boundary: “Canvas preview validates logical-binding syntax and rejects cross-Workspace provider references without provider I/O. It explicitly reports provider compatibility and readiness as not-checked. A passed preview is not permission, provider compatibility, availability, or Run admission; actual selection revalidates the exact declaration/provider contract and live grants.”

Documentation improvement: canonical file proposed docs/skills/repository-operations.md; durable boundary syntax/scope versus compatibility/readiness; evidence red/green/joined receipts; removes ambiguous unqualified logical-preview validation claim; actual provider integration remains unimplemented.

Upstream disposition: none. No root edits, RCC or external mutations.
