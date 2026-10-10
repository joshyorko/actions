# Proposed canonical documentation delta: #208 consumer classification

Target: `docs/skills/work-items.md`, in the native browser acceptance paragraph that currently says the authorization-denial stage has not yet produced a native artifact receipt.

Replace the stale passage with:

> Independent Linux frozen and Go-wrapper native runs both passed the normal, authorization-denied/sign-in-recovery, and storage-error stages at this source/build. Those scoped results do not cover missing bundled support or a generic HTTP 500: keep both states `NOT_RUN` until a hash-bound packaged browser stage exercises each real backend condition. Frontend tests with synthetic responses may verify message classification, but do not clear native acceptance.

Evidence binding: PR310 `ec8bea135569d98a3a63ef4f4f07b7dcc87e9f9d` / tree `82700f57df8a25c26d156d6e1738d1f64a4fa5c5`; issue #208 body SHA-256 `25cada9cee4ac8ca8aad7e47df4f4be58b010239d88dc3bd64f40cc2c97d26b9c`; frozen acceptance receipt `bca359b7fbd2e7303e618a74dcd6b869e23970b98a7bb810cc698ef2968fa71f`; Go-wrapper acceptance receipt `cd791fc251b7a400303d5846b32db4b44fdba101a3d812f409ece94b9d368440`. Both receipts retain `missing_runtime_support` and `generic_http_500` as `NOT_RUN`.
