# Independent PR290 frozen acceptance review

Disposition: **PASS for the exact hosted frozen-control acceptance tuple below. This is not general release acceptance.** Review is read-only; neither native binary nor RCC was executed locally.

## Exact source and workflow binding

- Control: PR290 branch `test/mcp-alias-frozen-control-20261010`, commit `fbd504a331acfeadf7fc64e013b4fefcda7412e4`, tree `0bddabdf6e6f85701b2b87f49e6c137cf48f532c`.
- Run `38067094994`, attempt 1, push event, completed/success; jobs `build` (`114256839712`) and `go_wrapper` (`114256839804`) completed/success.
- Native candidate `a47dc616069afdb0488aaed651abf0ceb9a82035`, tree `10e4b5fb3a3ee3d7c6b7c8ccbf5f6bfcdde70bc6`.
- Native build source `0045d91b2b5010b4b3706f777325e04b8eda805d`, tree `10e4b5fb3a3ee3d7c6b7c8ccbf5f6bfcdde70bc6`. GitHub commit readback confirms this is a merge of candidate a47 into `de2b9a884a7bf75320d0c3efb9294b8ec179c5c8` with the same exact tree as the candidate.
- The frozen selector pins resource-history test blob `69e2a468916f9982206573e8f5b71c6f2db8c8e7`; frozen workflow source and generated YAML are present in fbd. Harness runtime baseline is `c78288c3a0f07ba1013109c790f8e8b375a852d2` (tree `75a108db7d608e1316d59c96918213471409f31a`), distinct from candidate/runtime source.

## Native 11-case evidence

- Artifact `11675702008`, `frozen-catalog-rollback-fbd504a331acfeadf7fc64e013b4fefcda7412e4`, 111,828 bytes. Downloaded ZIP SHA-256 `90b2ace4381199eb6f39a5f256972896a90faa5423599ba061aa95ee1a29ad30`; it matches GitHub artifact metadata.
- ZIP members were inspected in memory; no broad extraction. Embedded JUnit has exactly the 11 pinned expected test identities, 11 tests, 0 failures, 0 errors, 0 skips. Exact fbd validator `action_server/scripts/verify_frozen_catalog_junit.py` was run against the archived XML and exited 0. Validator SHA-256 `8504eedc5beb363fe0d6f06fc442d74b600a108b4aff764f821dee6c2db4e02b`; archived native XML SHA-256 `cb4f87bfc0d3dc8b4e587fcefac3fd4004ea9d2bb3ba834af9989d1ce706636d`; strict output SHA-256 `8b301c36f67fa6626f79aa6d1570eb9bc057b3c55dfe0079e75eeac913fefc3a`.
- Native summary / artifact-verification JSON bind the result to candidate a47, source 0045, native build run `38060994147` attempt 1, native artifact `11673805091` (59,391,509 bytes; SHA-256 `26a60e999d62009ea83d70aac949a3c3bbf09895ea90119a7a39b2a05306e2f8`), resource-history blob above, and frozen binary SHA-256 `b4bfb975bc8b54cb6fc5408f3ea88e2a65bcb06324ffa72826d29a19d59f95a8`. Embedded test log reports `11 passed in 262.51s` (SHA-256 `9c6b768548aeab3faea5d7bd3c9a81d4f27c9daa8a5eddd27476a01397ba3bd6`).

## Separate Go-wrapper evidence

- Artifact `11676290980`, `frozen-catalog-go-wrapper-fbd504a331acfeadf7fc64e013b4fefcda7412e4`, 118,027 bytes. Downloaded ZIP SHA-256 `0bdae4a82bec1c1625bac490df6087795c14327ee55e0a560dfc621584c8d356`, matching GitHub artifact metadata.
- Its archived JUnit also passes the exact 11-case fbd validator: 11 tests, 0 failures, 0 errors, 0 skips; XML SHA-256 `8c2be3a34bacca2b9ce09373ba966a6debc0ff425592003ee85ed2954d649dd4`; strict validator output SHA-256 `8b301c36f67fa6626f79aa6d1570eb9bc057b3c55dfe0079e75eeac913fefc3a`.
- Go-wrapper receipt binds upstream native build run `38060994147`/attempt 1, native artifact `11673805091`, and separate wrapper artifact `11673147409` (77,810,317 bytes; ZIP SHA-256 `5caa374143633ed8faeb27fbd9aa6daf20b704e46599434af373685d02026764`). Wrapper source SHA-256 `dd0260b11a3fadf019058e55eb43fe96a2b85088793e1210c1d44835e343d293`, measurement receipt SHA-256 `e05e37a1f3194c518dd9ea22e19d4e01cfce15f991feaaf00a655b167c840910`; native byte-verification receipt SHA-256 `dc7725c13c273fbca186539f18b43bc2d3701f9e2704dc9b8b596de3112aa951`.
- The separate output receipt reports verified wrapper binary SHA-256 `26307ec2df6dee352048d4326dd246ffaa2cbcfa0f1e8bfbb35af86f34d9f07e` and frozen child SHA-256 `b4bfb975bc8b54cb6fc5408f3ea88e2a65bcb06324ffa72826d29a19d59f95a8`; the extracted child is recorded at `.actions/bin/action-server/internal/1.0.3/action-server`, executable mode, and matches the measured native binary.
- `wrapper-process-lifecycle.json` SHA-256 `c8b43edff887d5e7fa9487cb8e2dd46c1fcc107939eb69e2c23b5f2b5a704694` has 25 process records over the 11 expected node IDs. Every record has `identity_verified=true`, direct child-parent PID linkage, expected wrapper and child hashes, `natural_exit=true`, `stop_observed=true`, and `stop_failure=null`. The workflow test log reports `11 passed in 304.99s` (SHA-256 `ada46d7fc099306e0986995e2ea60b6e9b246596ef12f8a47fb4c14ec5d8937b`).

## Acceptance boundary and remaining status

This verifies the exact frozen-control candidate tuple a47 / source 0045 / tree 10e4b5, including the separate managed Go-wrapper path and its recorded natural shutdowns. It does not establish general release acceptance, other OS targets, broader behavior outside the selected cases, nor acceptance of current integration `e886`. The fbd branch still has the two devmode CI failures separately identified by root; those remain integration blockers and are not overridden by this passing acceptance run. No upstream defect was found. No additional canonical guide change is proposed: the existing evidence rules already require separate candidate/source and wrapper/native artifact identity receipts and explicit claim boundaries.
