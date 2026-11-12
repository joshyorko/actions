# Atomic generic enqueue replay marker

Installed a46 returned the same exact Work Item on idempotent enqueue but reported replay=false. Preserve that failure. The reviewed fix returns a private immutable item/replay result from the existing transactional request/audit branch, retaining enqueue()->str compatibility; the public adapter forwards the marker. No new preflight, authority or SQL writer is introduced.

Isolated regression43passed,3real-RCC skips,45PostgreSQL deselections. Independent source review found no blocker. Root integrates these exact bytes as Runtimea47; installed strict claimed Robot and PostgreSQL regression remain pending. a46 broad suite remains frozen in its original checkout while this candidate is prepared separately. Corea7 and Work Items a2 runtime payloads are unchanged.

The direct-Robot Canvas artifact denial was intended association enforcement, not a new authorization defect. The corrected harness must separate model/HTTP and fresh Canvas submit_input execution; prior observations are retained.

Child documentation proposals accepted and integrated. Upstream disposition:none.
