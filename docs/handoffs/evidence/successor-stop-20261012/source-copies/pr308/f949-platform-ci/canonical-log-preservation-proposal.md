Canonical target: docs/skills/repository-operations.md, alongside completed CI checkout evidence guidance.

Proposed exact paragraph:

Preserve a connector's completed-job decoded text as UTF-8 bytes without changing
its BOM or line endings. Record the decoder source, byte count, SHA-256, BOM
presence and CRLF count. This binds the received decoded text; it does not prove
the original HTTP or archive bytes. Give each job log one retrieval owner and
reuse the retained file for named-test and source-producer verification during
independent review.

Evidence: the once-fetched Linux and macOS f949 job logs both retain a UTF-8 BOM
and zero CRLF sequences, with byte counts and SHA-256 values in their extraction
and safe receipts. The selected connector explicitly returns decoded text.

Upstream disposition: none.
