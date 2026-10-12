# Retained provider reader observation under unknown tree ownership

Session-authorized bounded increment. Source base f949bef2eeab518ffd34d9e69955938a007f8922, tree ce5a94a37f108438daa9d2d283ab575b1000ce99. This design does not authorize a native launch or full controller.

Actual defect: cleanup_provider_until keeps its existing reader join inside the verified tree-ownership branch. An unconfirmed process birth prevents observation of an independently owned retained Thread, even when owner.process is the original caller object and reader.owner is that same original owner. The typed result reports unavailable reader facts rather than measured joined/alive/error facts.

Implementation: close the existing tree branch, then guard the unchanged existing reader join with _ProviderOwnership type plus exact owner.process identity and the existing _ProviderStartupReader type plus exact reader.owner identity. Reuse the same thread and supplied finite absolute endpoint; no replacement reader, additional loop, deadline origin, signal, fallback, lease query, or mode change.

Unknown root ownership remains False, preserves its fixed errors and refuses tree cleanup delegation. ProviderCleanupResult.complete still requires ownership confirmation, complete tree reaping, joined inactive error-free reader and no errors. Reader success cannot turn unknown process ownership into overall success. Changed object bindings remain unavailable.

Source controls: real finished Thread with unconfirmed capture; real blocked Thread with recorded remaining and zero timeout; unchanged Thread identity; ordinary join failure attached as fixed secondary class while original startup JSON failure/cause survive; changed original-process and reader-owner bindings never joined. All retained test threads are released/joined in bounded finally paths or are completed before observation.

Actual RED before source edit: all three new initial controls failed against exact f949 helper (finished reader unavailable, no blocked-reader join, join failure hidden as unavailable). Follow-up source uses only four inserted lines around the existing block. Full independent outer endpoint, final uncapped descendant census, passive lease design and native budgets remain held. The old full-controller design review is not adopted by this component change.

Upstream disposition: none.
