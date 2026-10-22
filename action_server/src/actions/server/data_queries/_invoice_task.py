"""Fixed synthetic invoice task. Reads sealed input and writes only its result file."""

import hashlib
import importlib.metadata
import json
import os
import sys
from pathlib import Path


def main():
    import actions.work_items

    source, target = map(Path, sys.argv[1:])
    raw = source.read_bytes()
    if len(raw) > 1024 * 1024:
        raise ValueError("bounded invoice execution input required")
    data = json.loads(raw)
    sdk = importlib.metadata.distribution("actions-work-items")
    origin = json.loads(sdk.read_text("direct_url.json"))
    module = Path(actions.work_items.__file__).resolve()
    owned = {Path(sdk.locate_file(f)).resolve() for f in sdk.files or ()}
    module_digest = hashlib.sha256(module.read_bytes()).hexdigest()
    wheel_digest = origin.get("archive_info", {}).get("hashes", {}).get("sha256")
    if (
        sdk.version != "0.5.0a1"
        or module not in owned
        or not module.is_relative_to(Path(sys.prefix).resolve())
        or module_digest != data["sdk_module_sha256"]
        or wheel_digest != data["worker_input"]["sdk_wheel_sha256"]
    ):
        raise ValueError("installed SDK candidate differs")
    rows = data["rows"]
    if not isinstance(rows, list) or not all(
        isinstance(row, dict)
        and set(row) == {"invoice_id", "customer", "amount_cents", "days_overdue"}
        and isinstance(row["amount_cents"], int)
        and not isinstance(row["amount_cents"], bool)
        for row in rows
    ):
        raise ValueError("typed sealed invoice rows required")
    result = {
        "version": "actions.invoice-task-result/v1",
        "effect_policy": "private-result-file-only",
        "binding": data["worker_input"]["proposal"]["binding"],
        "review_id": data["worker_input"]["proposal"]["review_id"],
        "claim": data["claim"],
        "fence": data["fence"],
        "execution_input_digest": hashlib.sha256(raw).hexdigest(),
        "invoice_count": len(rows),
        "total_cents": sum(row["amount_cents"] for row in rows),
        "sdk": {
            "version": sdk.version,
            "wheel_sha256": wheel_digest,
            "module_sha256": module_digest,
        },
        "python": ".".join(map(str, sys.version_info[:3])),
    }
    temporary = target.with_suffix(".partial")
    with temporary.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(result, sort_keys=True, separators=(",", ":")) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(target)


if __name__ == "__main__":
    main()
