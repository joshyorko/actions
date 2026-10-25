# Explicit compatibility endpoints and retired vendor publishers

Missing/empty/whitespace cloud endpoints now fail before HTTP. Existing explicit hostname/HMAC behavior remains; no local credential/config changes occurred. Prompt cannot select an absent default.7 Runtime cloud tests passed; initial3failure/1pass regression retained.

Both legacy vendorS3 template workflows (community beta and manual production) are removed; local packaging remains. Workflow/release regressions passed12; initial vendorpublisher1failure then intermediate1failure identifying the second workflow are retained. No alternate publication target is invented or deployed. Independent review found no blockers; its recommended whitespace case is included in final7pass.

Canonical guide updated. Installedcloud flow and full sovereignty remain unqualified. Upstream disposition:none.
