Documentation improvement:
- Canonical file proposed: docs/skills/repository-operations.md
- Placement: with completed CI log preservation/source-producer evidence guidance.
- Exact paragraph:

Preserve a decoded job log exactly before parsing. A Windows decoded log can mix
CRLF with isolated LF and carry a UTF-8 BOM; read and hash its bytes, then keep
summaries and named-test events in a separate derived receipt. Matching test text
after newline normalization does not establish artifact-byte identity. Label the
artifact as connector-decoded UTF-8 text unless original HTTP or archive bytes
were also retained.

- Durable learning captured: decoded Windows log bytes can contain mixed newline forms, so normalized text comparisons support event extraction but cannot substitute for the retained artifact digest.
- Evidence: once-fetched completed Windowsjob114685788075 saved747820bytes SHA680bf188..., BOMtrue,5409CRLF and5411LF (twoisolatedLF). ExactUTF8 encode/decode roundtrip; all11namedPASS events and bothsummaries independently matched. Linux/Mac sibling safe receipts report BOMtrue with0CRLF; no siblinglogs refetched.
- Stale or ambiguous guidance removed: treating UTF-8 decoding or matching parsed lines as proof of original HTTP/archive identity, or assuming one uniform Windows newline style.
- Remaining uncertainty: original transport/archive bytes were not retained; producer identity relies on saved GitAPI record and logged checkout, not a newly fetched local commit. General24check success and source/frozen suites do not qualify the independently held native baseline or release gates.
Upstream disposition: none.
