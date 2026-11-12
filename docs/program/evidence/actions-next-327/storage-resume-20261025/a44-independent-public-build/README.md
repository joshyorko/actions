# Independent public-input rebuild for a44 native preparation

SOURCE-ONLY, NOT EXECUTED. This is a separate rebuild from public dependency sources and the already obtained original owned Core a6 wheel. It does not access, export, copy or retry upload of the denied 77 MB archive. Library byte PUT Forbidden remains a denial; no alternative route for that blob is authorized or implemented. Root publishes these source files/manifests on the existing release branch; parent obtains that source checkpoint and builds in its normal authorized network namespace.

## Inputs and provenance

Original source checkpoint: d0c87a38a937cc339e8e661ac453c7a62ed41fa6; installed original Runtime 1.1.0a44 wheel SHA256 1502214a6a6319521984d554244aca502659fc919d5a31bac94727d3e534104c. Original Core 1.1.0a6 wheel SHA256 718ea63637f096d26c4de5f82ca736eec1358b197d0a63883c063ad205e0860e must already exist in candidate/wheels. Core a6 is owned candidate input, NOT a request to public PyPI for actions-core1.1.0a6. No credentials, private indexes or signed download URLs are needed or supplied by these scripts.

prepare-public-producer.py derives from committed docs/program/evidence/actions-next-327/storage-resume-20261025/a44-managed-host/compiler/prepare-compiler-managed.py (original SHA256 6b97c262bc6e807b72959f732586a2aa337d504108900921813310ab60b3e3af, recorded at commit786d136426a7c3aa097894ce6121ff8d817974a7). verify-core.py is byte-identical to original a44 verifier SHA256 a69b5a9e9e45b87803c89068c17210891040ee92171b6db0b604e06e5adf554d. Target recipe/validator templates reuse the reviewed fixed-path offline flow with all prior archive pins replaced by refusing placeholders. source-hashes.json covers the delivered source templates and public manifest. Nothing here contains cache/archive bytes.

PUBLIC-DEPENDENCIES.json retains the requested 26 conda identities (name/version/build/public URL/SHA256 ) and 19 Python distribution identities (name/version/installed METADATA SHA256 ). The fresh build must match exactly or fail before export. These Python hashes identify installed METADATA bytes, NOT wheel archives; this check must not be described as independent wheel-download hash verification. Conda SHA values are compared to the package records maintained by the fresh standard public resolver, not to retained downloaded archives. The manifest's prose source labels are retained verbatim; identity comparison uses explicit fields, not those labels. Only the owned Core wheel additionally has its actual wheel bytes and all 87 installed payload members independently compared here.

## Producer command

Both producer and eventual native target must use exactly /tmp/actions327-a44-offline-v1/compiler in their respective filesystem namespaces. It must not exist, and ancestors must be canonical nonsymlink directories. Do not change embedded catalog paths. Do not reuse an earlier failed root. Parent creates only its own parent/export-parent directories normally; no unrelated cleanup is required or performed.

    mkdir -p /tmp/actions327-a44-offline-v1
    /producer/a44/consumer/bin/python -I /source/native-independent-public-build/prepare-public-producer.py \
      --candidate-base /producer/a44 \
      --compiler-root /tmp/actions327-a44-offline-v1/compiler \
      --export-root /producer/new-independent-export

The export root must be fresh, outside the compiler tree, and on the same filesystem. All six shipped source/manifest files must remain together. Use the original installed a44 consumer with its exact wheels and bundled RCC 18.19.3 SHA256 7e588c01751ca2ae15ba13ef67f2f4b7567697a5a8389737059a73936f509428. Run directly with consumer Python; do not wrap it in RCC or change proxy/TLS/security/network settings. The producer starts standard env publish from public sources using fresh HOME/ROBOCORP_HOME and local PIP_FIND_LINKS containing only the owned Core wheel. Standard /usr/sbin:/sbin PATH is retained.

Resource bounds remain initial free>=4.25GiB, compiler allocated<2GiB, free reserve>=1GiB; raw combined process logs 12 MiB; version 30s / publish 600s / proof 180s / export 120s. Fresh export is additionally limited to 100 MiB and validator limits uncompressed archive entries to 100 MiB and each decoded catalog to 8 MiB. Export is outside compiler allocation but consumes the same free-space reserve. Sampling is not a quota and temporary peak is not proven by initial estimates. Cleanup remains independent bounded process-group/descendant phases with subreaper restore. Parent supplies adequate outer supervision if interrupting the script; no security overrides are introduced.

After successful fresh publish/proof, qualify-export.py rechecks every Core payload against the owned wheel, compares all public identities and validates EVERY compressed catalog before export. Exactly these two catalog names are permitted:

- 05bce139c5c902c0v12.linux_amd64
- 4240e3dcbf7fa40dv12.linux_amd64

Both catalogs must embed the exact fixed holotree base, expected RCC/platform, valid entry names and contained relative symlinks. Only then does the supported command run:

    rcc holotree export 05bce139c5c902c0v12.linux_amd64 4240e3dcbf7fa40dv12.linux_amd64 --zipfile /producer/new-independent-export/independently-built-public-cache.zip

It runs with the NEW producer's ROBOCORP_HOME, not any earlier cache. No trust, HOME, receipts, configuration, artifact provider or authorization files are exported. Final ZIP validation allows only exact catalog entries and library objects, rejecting all other paths. The fresh archive may have a different hash/size; generated target recipe and validator pin those measured fresh bytes. Require producer exit 0 AND independent-export-manifest.json status FRESH_EXPORT_VALIDATED. A partial core proof/config fragment is not export qualification.

## Target continuation

Only the NEW independently built artifact and generated source recipe are eligible for the parent's own supported native import. No source-only delivery or producer PASS establishes that import. Producer trust and proof evidence remain local. The target uses its already obtained original a44 consumer/Core wheel and starts with its own fresh fixed compiler root. If producer and target share one filesystem, stop: freshness cannot coexist at that same path; use the intended separate namespaces or an explicitly owner-managed lifecycle, never silent deletion/moving trust by this script.

Parent validates the new manifest/hash and runs from the new export directory:

    /native/a44/consumer/bin/python -I /new-independent-export/prepare-offline-managed.py \
      --candidate-base /native/a44 \
      --compiler-root /tmp/actions327-a44-offline-v1/compiler \
      --public-cache /new-independent-export/independently-built-public-cache.zip

Generated target source retains supported holotree import --strict, env publish --no-build --provider local, newly generated target trust and isolated no-build 87-member Core proof. Target profile requires 3 GiB initial free after archive receipt,2GiB compiler cap,1GiB reserve,12MiB logs / import 120s / publish 600s / proof 180s. Only its newly observed target-config-fragment.json may configure native execution. Native import, GUI and parent visual review remain pending.

## Verification and canonical delta

Here: all source/template files AST-parsed; embedded package, explicit source/root/identity guards and refusing template placeholders inspected. No producer/helper/target script executed, no build/RCC/network/artifact transfer attempted. Public manifest 26/19 counts statically checked. Root reviews before parent execution; any dependency drift fails without changing pins or silently falling back to a prior cache.

Proposed docs/skills/repository-operations.md addition: “A denied artifact transfer remains denied. An independently authorized public-input rebuild must start from source and already owned candidate inputs, authenticate the newly observed dependency identities, and derive export/target pins from its own fresh output. Metadata hashes identify installed metadata, not distribution archives. Preserve producer trust locally; supported target import must create new target trust and re-prove payload bytes. Never treat source delivery, producer evidence or a different archive's historical hash as native acceptance.”

Upstream disposition: none. Owned source-only build recipe; no upstream modification or issue publication.
