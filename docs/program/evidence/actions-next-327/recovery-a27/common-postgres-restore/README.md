# Installed common PostgreSQL restore qualification

Runtime 1.1.0a27, source `fdc38d7090c4ac470171c499e77eab636fd452e6`, noneditable wheel SHA256 `812d8b742b81d74f94ef3ed39132b25bcc59a25727851f0f35d8d7e8798e9147`.

The retained harness executed one real generated consumer through RCC using synthetic authorized common services and an owned pinned PostgreSQL container. After quiescence, it dumped the common schema, pinned and copied immutable filesystem objects, and restored to a separate database. Two fresh installed-consumer processes reproduced the exact execution snapshot, historical claim, Run/Attempt and four artifact byte/digest readbacks. Original object bytes remained unchanged; the owned container was removed. No source engine overlay was loaded.

See `receipt.json`, `before.json`, and both restored-process receipts. Database dumps, context files containing disposable connection credentials, and artifact bodies are deliberately excluded. The scripts retain the exact executable procedure and synthetic fixture configuration.

This qualifies same-version quiescent common PostgreSQL plus filesystem-object restoration. It does not qualify ordinary CLI PostgreSQL configuration, active job/effect recovery, RCC cache loss, cross-version downgrade, production storage, or credentials. SQLite and legacy attachment restore remain separate evidence cells. Upstream disposition: none.
