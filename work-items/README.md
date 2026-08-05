# actions-work-items

`actions-work-items` is a Python producer-consumer work item library for local
automation, services, ETL pipelines, and queues. It provides the familiar
`from actions import workitems` workflow while preserving parent-linked output,
JSON payloads, and file attachments.

## Installation

```bash
pip install actions-work-items
```

Optional backends:

```bash
pip install "actions-work-items[redis]"
pip install "actions-work-items[docdb]"
pip install "actions-work-items[all]"
```

## Backend Support

| Backend | Maturity | Scope and evidence |
| --- | --- | --- |
| SQLite | Release-critical | Default persistent backend; covered by the package release gate and concurrency tests. |
| FileAdapter | Stable local | Local, single-process Control Room-style JSON files; covered by adapter tests. |
| Redis | Experimental | Optional distributed backend; service-backed reliability coverage is not yet in the release gate. |
| MongoDB / DocumentDB | Experimental | Optional backend with GridFS support; service-backed reliability coverage is not yet in the release gate. |
| Action Server | SQLite integration | REST, scheduler, and trigger paths use a datadir-owned SQLite adapter; the server does not manage arbitrary adapters. |

SQLite and FileAdapter are the release-supported local choices. Redis and
DocumentDB are available for evaluation, but their experimental status is part
of the 0.3.0 contract.

## Quick Start

Seed an input, reserve it, create a parent-linked output, and release the input:

```python
from actions import workitems
from actions.work_items import SQLiteAdapter


workitems.init(SQLiteAdapter(queue_name="orders", output_queue_name="orders_done"))
workitems.seed_input(payload={"order_id": "A-1001"}, queue_name="orders")

item = workitems.inputs.reserve()
try:
    workitems.outputs.create(
        payload={"order_id": item.payload["order_id"], "status": "processed"},
    )
    item.done()
except Exception:
    item.fail()
    raise
```

For automatic success/failure release, iterate with a context manager:

```python
from actions import workitems


for item in workitems.inputs:
    with item:
        workitems.outputs.create(payload={"source": item.payload, "ok": True})
```

`workitems.inputs.current` is the reserved item while it is in flight;
`workitems.outputs.last` is the most recently created output.

## Payloads

Payloads may be any JSON-serializable value. A dictionary is common:

```python
from actions import workitems


for item in workitems.inputs:
    with item:
        order_id = item.payload["order_id"]
        workitems.outputs.create(
            payload={"order_id": order_id, "status": "validated"}
        )
```

## Files

Work items can carry files in addition to payload data:

```python
from actions import workitems


for item in workitems.inputs:
    with item:
        for name in item.list_files():
            content = item.get_file(name)
            print(name, len(content))

        output = workitems.outputs.create(payload={"status": "files-attached"}, save=False)
        output.add_file(path="./output/report.pdf")
        output.save()
```

Files can be added one at a time or with glob patterns:

```python
item.add_file(path="./report.pdf")
item.add_files("./output/*.csv")
item.remove_file("temporary.csv", missing_ok=True)
```

`outputs.create(files={...})` accepts a mapping of safe work item names to
local paths or bytes. `get_file()` returns bytes and can also write them to a
path. `get_email()` parses an attached email file.

## Failures

Business failures describe invalid or unexpected data; application failures
describe runtime or infrastructure problems:

```python
from actions import workitems
from actions.work_items import ExceptionType


for item in workitems.inputs:
    if not item.payload.get("order_id"):
        item.fail(ExceptionType.BUSINESS, code="MISSING_ORDER_ID", message="Required")
        continue
    try:
        process(item.payload)
    except TimeoutError as exc:
        item.fail(ExceptionType.APPLICATION, code="TIMEOUT", message=str(exc))
        continue
    item.done()
```

Typed `BusinessException` and `ApplicationException` may also be raised inside
an item context manager; the context manager releases the item accordingly.

## Adapter Configuration

Explicit SQLite setup:

```python
from actions.work_items import SQLiteAdapter, init


init(SQLiteAdapter(
    db_path="./workitems.db",
    queue_name="orders",
    output_queue_name="orders_done",
    files_dir="./work_item_files",
))
```

SQLite environment variables are `RC_WORKITEM_DB_PATH`,
`RC_WORKITEM_QUEUE_NAME`, `RC_WORKITEM_OUTPUT_QUEUE_NAME`, and
`RC_WORKITEM_FILES_DIR`.

FileAdapter setup:

```python
from actions.work_items import FileAdapter, init


init(FileAdapter(input_path="./output/work-items-in", output_path="./output/work-items-out"))
```

Its environment variables are `RC_WORKITEM_INPUT_PATH` and
`RC_WORKITEM_OUTPUT_PATH`.

Redis and DocumentDB require their optional extra and can be selected with
`create_adapter("redis")` or `create_adapter("documentdb")`. Redis uses
`RC_REDIS_URL`; DocumentDB uses `DOCDB_URI`, `DOCDB_DATABASE`, and the queue
variables. `RC_WORKITEM_ADAPTER` can name an adapter class; without an explicit
adapter, environment-based selection falls back to SQLite.

## Action Server Integration

Action Server exposes work item state through REST endpoints backed by the
server's datadir-owned SQLite adapter:

```bash
curl -X POST http://localhost:8080/api/work-items \
  -H "Content-Type: application/json" \
  -d '{"payload": {"order_id": "A-1001"}, "queue_name": "orders"}'
curl 'http://localhost:8080/api/work-items?queue_name=orders&state=PENDING'
curl 'http://localhost:8080/api/work-items/stats?queue_name=orders'
```

This integration does not make the Action Server UI/API a manager for Redis,
DocumentDB, or custom adapters.

## Safety and Determinism

- Attachment names are a single safe filename component. Empty/dot names,
  absolute paths, path separators, quotes, and C0 controls are rejected.
- Item IDs and persisted attachment paths are validated after resolution;
  symlink escapes and root-equal item directories are rejected.
- SQLite reservation uses an immediate transaction, FIFO `created_at` ordering
  with `rowid` tie-breaking, conditional claiming, and rollback on errors.
- JSON payload reads preserve every valid JSON shape and reject malformed stored
  JSON rather than silently changing it.
- Queue and output queue names remain explicit across producer, consumer,
  scheduler, trigger, and preloaded-action boundaries.

These guarantees are covered by the package's filesystem, SQLite, serializer,
and integration tests; Redis and DocumentDB still require service-backed gates
before production claims are appropriate.

## API Summary

- `workitems.init(adapter=None)`, `create_adapter(type=None, **kwargs)`
- `workitems.seed_input(payload, files=None, queue_name=None)`
- `workitems.inputs.reserve()` / `get_input()`
- `workitems.outputs.create(payload=None, files=None, save=True)`
- `Input`, `Output`, `EmptyQueue`, `BusinessException`, and
  `ApplicationException`
- `State.DONE.value` is `DONE`; incoming `COMPLETED` is accepted as a
  compatibility alias.

## Migrating from robocorp-workitems

The common lifecycle is intentionally similar, but this is not a byte-for-byte
Control Room clone:

```python
# Before
from robocorp import workitems

# After
from actions import workitems
```

Reserve an input before calling `outputs.create()`; this package requires the
parent link. `inputs.current` is `None` until reservation, and
`outputs.create(files=...)` accepts a file-name-to-path-or-bytes mapping.
`get_file()` returns bytes, while `get_email()` parses an attached email rather
than providing Robocorp's payload-oriented `Input.email()` helper.

The distribution-name alias is import-safe:

```python
from actions_work_items import workitems
```

## Compatibility and Version Check

Verify the public aliases resolve to the same singleton API and report the
installed release version:

```python
import importlib.metadata

import actions.work_items
import actions.workitems
import actions_work_items


assert actions.work_items.inputs is actions.workitems.inputs
assert actions_work_items.workitems is actions.workitems
assert actions.work_items.__version__ == actions_work_items.__version__
assert actions.work_items.__version__ == importlib.metadata.version("actions-work-items")
```

For bugs or compatibility questions, use the
[issue tracker](https://github.com/joshyorko/actions/issues) and include the
package version, adapter, minimal lifecycle, and reproducible error.

## License

Apache 2.0.
