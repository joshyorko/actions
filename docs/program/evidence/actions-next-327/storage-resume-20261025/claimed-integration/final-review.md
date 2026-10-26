# Claimed Robot integration review

Disposition: no blocking defect identified in the reviewed diff. Read-only source and regression-design review; no tests, RCC, PostgreSQL, or installed candidate execution performed in this lane. Parent-reported combined test outcomes are not independently rerun here.

Reviewed invariants:
- Robot authority is issued outside SQL after provider verification, tied to owner/caller/ticket identity, and backed by a captured/rechecked Package SQL pin. Bound callbacks retain fresh SQL grants and deployment checks. Runner additionally checks current activated deployment.
- Generic transaction takes Run counter/workspace locks; Robot publication performs final fence, claim, and COMPLETE checks and finishes Run/Attempt/outputs and queue claim in one transaction. Heartbeat keeps claim and Attempt renewal atomic.
- Retained terminal receipt checks immutable snapshot/policy/input and claim epoch against SQL while allowing expired leases after terminal completion. Output access remains separate from metadata acknowledgements.
- ASCII-escaped canonical Robot input encoding is shared between admission, selection and receipt validation. Oversized ASCII and Unicode tests assert no added queue/request/Run/Attempt rows; exact 65536-byte tests preserve admission. Scoped missing/malformed Robot metadata rejects rather than silently bypassing the guard.
- Default none declaration is omitted to preserve historical manifest bytes. Nondefault declarations remain canonical and manifest-bound; producer/output modes reject.
- Knowledge compatibility expands only exact Core a7 alongside a4, keeping the prior draft compatibility contract. Fixture repairs instantiate real TaskService and preserve helper-byte assertion except the explicit reviewed JSON model conversion.

Regression-design limitation: the terminal/cancel contender test signals immediately before its cancellation call. It demonstrates outcome consistency but does not prove the contender has reached a database lock wait. This is not a correctness blocker; late committed mutation and renewal rollback tests independently exercise deterministic boundaries. Installed a46 behavior still requires parent-owned qualification.

## Proposed canonical documentation delta
Append to docs/skills/work-items.md:

“Robot Work Item inputs must fit both the queue policy and the exact canonical Robot carrier (65536 bytes, ASCII-escaped JSON). Apply the carrier check before queue or Run admission; a UTF-8 policy-size check alone is insufficient for non-ASCII inputs. Prepare provider-backed Robot authority outside SQL, then recheck its immutable Package pin and current grants/fences using SQL within publication. Complete the claim and Run/Attempt/artifact transition in the same transaction. Retained terminal receipts validate immutable claim provenance without requiring a still-live lease; metadata acknowledgement never grants output access. Preserve the omitted default-none declaration so existing Robot revision preimages remain unchanged.”

Evidence: robot_work_item_authority.py; generic_work_item_execution.py (_inputs, _transaction, _authority_projection); robot_runtime_runner.py (publish_robot); robot_receipts.py; test_robot_claimed_input_bounds_327.py; test_robot_claimed_races_327.py; test_robot_claimed_terminal_receipts_327.py; contract test_robot_work_item_declaration_327.py. Exact reviewed source fingerprints are adjacent.

Documentation-improvement receipt: proposed exact canonical delta to root, shared docs not modified by this lane. Upstream disposition: none. No upstream defect identified or external mutation performed.
