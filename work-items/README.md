# actions-work-items

`actions-work-items` is a Robocorp-style work item library for Python
producer-consumer workflows. It keeps the familiar common path:

```python
from actions import workitems
```

usage shape while supporting local files, SQLite, Redis, and
MongoDB-compatible DocumentDB backends.

## Installation

```bash
pip install actions-work-items
```

Optional backend dependencies:

```bash
pip install "actions-work-items[redis]"
pip install "actions-work-items[docdb]"
pip install "actions-work-items[all]"
```

## Work Item Model

Work items carry data from one step of a workflow to the next.

Each step reads input work items from an input queue. While processing a
reserved input, the step can create output work items for the next queue. This
follows the main Robocorp work item model:

- `workitems.inputs` reads and reserves input items.
- `workitems.outputs` creates output items.
- `item.payload` contains JSON-serializable data.
- `item.done()` releases an input as successfully processed.
- `item.fail()` releases an input as failed.

An output item is created while an input item is reserved. That parent input is
what gives the workflow traceability from one step to the next.

Unlike a Robocorp Control Room run, a local `actions-work-items` run does not
automatically start with a reserved input item. Seed or provide input items with
one of the adapters, then reserve or iterate them.

## Getting Started

Reserve one input item and create one output item:

```python
from actions import workitems


def handle_item():
    item = workitems.inputs.reserve()
    print("Received payload:", item.payload)

    workitems.outputs.create(payload={"status": "processed"})
    item.done()
```

After an item is reserved, it is available as `workitems.inputs.current` until
it is released:

```python
item = workitems.inputs.reserve()
assert workitems.inputs.current is item
```

Iterate over every available input item:

```python
from actions import workitems


def handle_all_items():
    for item in workitems.inputs:
        print("Received payload:", item.payload)
        workitems.outputs.create(payload={"source": item.payload, "ok": True})
        item.done()
```

Use a context manager when you want automatic release behavior:

```python
from actions import workitems


def handle_all_items():
    for item in workitems.inputs:
        with item:
            workitems.outputs.create(payload={"source": item.payload, "ok": True})
```

## Payloads

A payload can be any JSON-serializable value. Most workflows use a dictionary:

```python
from actions import workitems
from actions.work_items import ExceptionType


for item in workitems.inputs:
    with item:
        order_id = item.payload["order_id"]
        workitems.outputs.create(
            payload={
                "order_id": order_id,
                "status": "validated",
            }
        )
```

To seed an input queue directly from Python, use `seed_input`:

```python
from actions import workitems


workitems.init()
workitems.seed_input(
    payload={"order_id": "A-1001"},
    queue_name="orders",
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

        output = workitems.outputs.create(
            payload={"status": "files-attached"},
            save=False,
        )
        output.add_file(path="./output/report.pdf")
        output.save()
```

Files can be added one at a time or with glob patterns:

```python
item.add_file(path="./report.pdf")
item.add_files("./output/*.csv")
item.remove_file("temporary.csv", missing_ok=True)
```

When creating an output directly, `files` is a mapping of work item names to
local paths or bytes:

```python
workitems.outputs.create(
    payload={"status": "complete"},
    files={"report.pdf": "./output/report.pdf"},
)
```

## Failures

Use `fail()` when an item cannot be completed. Business failures are expected
data or validation problems. Application failures are runtime or infrastructure
problems that may be retried by the surrounding workflow.

```python
from actions import workitems


for item in workitems.inputs:
    if not item.payload.get("order_id"):
        item.fail(
            ExceptionType.BUSINESS,
            code="MISSING_ORDER_ID",
            message="Payload must include order_id.",
        )
        continue

    try:
        process(item.payload)
    except TimeoutError as exc:
        item.fail(
            ExceptionType.APPLICATION,
            code="TIMEOUT",
            message=str(exc),
        )
        continue

    item.done()
```

You can also raise typed exceptions inside a context manager:

```python
from actions import workitems
from actions.work_items import BusinessException


for item in workitems.inputs:
    with item:
        if not item.payload.get("order_id"):
            raise BusinessException("Missing order_id", code="MISSING_ORDER_ID")
```

## Backend Adapters

The default adapter is SQLite. You can also select an adapter explicitly in code
or through environment variables.

### SQLite

```python
from actions.work_items import SQLiteAdapter, init


adapter = SQLiteAdapter(
    db_path="./workitems.db",
    queue_name="orders",
    output_queue_name="orders_done",
    files_dir="./work_item_files",
)
init(adapter)
```

Environment variables:

- `RC_WORKITEM_DB_PATH`: SQLite database path.
- `RC_WORKITEM_QUEUE_NAME`: Input queue name.
- `RC_WORKITEM_OUTPUT_QUEUE_NAME`: Output queue name.
- `RC_WORKITEM_FILES_DIR`: File attachment directory.

### File

```python
from actions.work_items import FileAdapter, init


adapter = FileAdapter(
    input_path="./output/work-items-in",
    output_path="./output/work-items-out",
)
init(adapter)
```

Environment variables:

- `RC_WORKITEM_INPUT_PATH`: Input directory.
- `RC_WORKITEM_OUTPUT_PATH`: Output directory.

### Redis

> **Experimental:** Redis is not part of the current release reliability gate and does not yet have service-backed CI coverage.

Install Redis support before using this adapter:

```bash
pip install "actions-work-items[redis]"
```

```python
from actions.work_items import create_adapter, init


adapter = create_adapter("redis")
init(adapter)
```

Environment variables:

- `RC_REDIS_URL`: Redis connection URL.
- `RC_WORKITEM_QUEUE_NAME`: Input queue name.
- `RC_WORKITEM_OUTPUT_QUEUE_NAME`: Output queue name.
- `RC_WORKITEM_FILES_DIR`: File attachment directory.

### MongoDB / DocumentDB

> **Experimental:** DocumentDB is not part of the current release reliability gate and does not yet have service-backed CI coverage.

Install DocumentDB support before using this adapter:

```bash
pip install "actions-work-items[docdb]"
```

```python
from actions.work_items import create_adapter, init


adapter = create_adapter("documentdb")
init(adapter)
```

Environment variables:

- `DOCDB_URI`: MongoDB or DocumentDB connection URI.
- `DOCDB_DATABASE`: Database name.
- `RC_WORKITEM_QUEUE_NAME`: Input queue name.
- `RC_WORKITEM_OUTPUT_QUEUE_NAME`: Output queue name.
- `RC_WORKITEM_FILE_SIZE_THRESHOLD`: GridFS threshold for large files.

## Environment-Based Adapter Selection

When `workitems.init()` is called without an adapter, the library can build an
adapter from environment variables:

```bash
export RC_WORKITEM_ADAPTER=actions.work_items.SQLiteAdapter
export RC_WORKITEM_DB_PATH=./workitems.db
export RC_WORKITEM_QUEUE_NAME=orders
export RC_WORKITEM_OUTPUT_QUEUE_NAME=orders_done
```

Then initialize normally:

```python
from actions import workitems


workitems.init()
```

## Action Server Integration

The Action Server integration exposes work item state through REST endpoints:

```bash
curl -X POST http://localhost:8080/api/work-items \
  -H "Content-Type: application/json" \
  -d '{"payload": {"order_id": "A-1001"}, "queue_name": "orders"}'

curl http://localhost:8080/api/work-items?queue_name=orders&state=PENDING
curl http://localhost:8080/api/work-items/stats?queue_name=orders
```

## API Summary

Core objects:

- `workitems.inputs`: input queue collection.
- `workitems.outputs`: output queue collection.
- `workitems.inputs.current`: current reserved input item.
- `workitems.outputs.last`: most recently created output item.

Common functions:

- `workitems.init(adapter=None)`: initialize the work item context.
- `workitems.create_adapter(type=None, **kwargs)`: create a backend adapter.
- `workitems.seed_input(payload, files=None, queue_name=None)`: seed an input.
- `workitems.get_input()`: reserve the next input.
- `workitems.create_output(payload=None, files=None, save=False)`: create output.

Common classes and exceptions:

- `Input`: input work item with `payload`, `done()`, `fail()`, and files.
- `Output`: output work item with `payload`, files, and `save()`.
- `EmptyQueue`: no input item is available.
- `BusinessException`: expected validation or data failure.
- `ApplicationException`: runtime or infrastructure failure.

## Robocorp Compatibility Notes

The common producer-consumer flow is intentionally close to
`robocorp-workitems`, but this package is not a byte-for-byte clone of the
Control Room library.

- Import from `actions`, not `robocorp`: `from actions import workitems`.
- `inputs.current` is `None` until this package reserves an input. Use
  `inputs.reserve()` or iterate `inputs` first.
- `outputs.create()` requires a reserved input, matching Robocorp's traceability
  rule.
- `outputs.create(files=...)` accepts a mapping of file name to path or bytes.
- `get_file()` returns bytes. If a path is provided, it also writes those bytes
  to disk.
- `get_email()` parses an attached email file. It is not the same method as
  Robocorp's Control Room payload-oriented `Input.email()` helper.
- `State.DONE.value` is `DONE`; incoming `COMPLETED` values are accepted as a
  compatibility alias.

## Migration from robocorp-workitems

Most code only needs to change the import:

```python
# Before
from robocorp import workitems

# After
from actions import workitems
```

The package also provides a Python-safe distribution-name alias:

```python
from actions_work_items import workitems
```

## License

Apache 2.0.
