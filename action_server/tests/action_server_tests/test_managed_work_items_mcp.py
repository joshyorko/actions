"""Isolated model facade tests; host wiring and SQL acceptance live elsewhere."""

import asyncio
import json
import threading
from uuid import uuid4

from actions.server.managed_work_items.contracts import (
    Capabilities,
    ManagedCaller,
    Operation,
    Permission,
    QueueRef,
)
from actions.server.managed_work_items.mcp import (
    ManagedWorkItemsMcp,
    _item_view,
    _project_result,
    _queue_key,
    _schema,
)
from actions.server.run_outputs.types import Actor


def _queue(workspace: str, queue_id: str, deployment: str | None = None) -> QueueRef:
    deployment_id = deployment or str(uuid4())
    return QueueRef.model_validate_json(
        json.dumps(
            {
                "workspace_id": workspace,
                "deployment": {
                    "workspace_id": workspace,
                    "deployment_id": deployment_id,
                    "revision_id": "sha256:" + "a" * 64,
                },
                "queue_id": queue_id,
            }
        )
    )


def test_missing_publication_or_authentication_denies_catalog_and_calls():
    caller = ManagedCaller(actor=Actor(principal_id=str(uuid4())))

    async def auth(_):
        return caller

    async def check():
        denied = ManagedWorkItemsMcp(object(), auth)
        assert await denied.tools(object()) == []
        result = await denied.call(
            object(),
            "managed_queues_list",
            {"operation": "queues.list", "workspace_id": str(uuid4())},
        )
        assert result.is_error
        unauthenticated = ManagedWorkItemsMcp(object(), None, object())
        assert await unauthenticated.tools(object()) == []

    asyncio.run(check())


def test_catalog_and_each_call_require_publication_and_current_grants():
    workspace = str(uuid4())
    caller = ManagedCaller(actor=Actor(principal_id=str(uuid4())))

    class Policy:
        enabled = True
        checks = 0
        queue = _queue(workspace, "published")

        def workspaces(self, identity):
            assert identity == caller
            return [workspace]

        def allows(self, identity, requested, operation):
            self.checks += 1
            return (
                self.enabled
                and identity == caller
                and str(requested.root) == workspace
                and operation == Operation.QUEUES
            )

        def queues(self, identity, requested, operation):
            assert identity == caller
            if str(requested.root) == workspace and operation == Operation.QUEUES:
                return [self.queue]
            return []

    class Port:
        enabled = True
        calls = 0
        thread_ids = set()

        def capabilities(self, identity, requested):
            self.thread_ids.add(threading.get_ident())
            assert identity == caller
            operations = (Operation.QUEUES,) if self.enabled else ()
            permissions = (Permission.READ,) if self.enabled else ()
            return Capabilities(
                runtime_version="1.1.0a13",
                sdk_version="0.5.0a1",
                workspace_id=requested,
                operations=operations,
                permissions=permissions,
                backend="sqlite",
                modes=("producer",),
            )

        def call(self, identity, command):
            self.calls += 1
            self.thread_ids.add(threading.get_ident())
            assert identity == caller
            assert command.operation == "queues.list"
            return {"queues": [], "next_cursor": None, "server_time_ms": "1"}

    port, policy = Port(), Policy()

    async def auth(_):
        return caller

    async def check():
        event_loop_thread = threading.get_ident()
        facade = ManagedWorkItemsMcp(port, auth, policy)
        catalog = await facade.tools(object())
        assert [tool.name for tool in catalog] == ["managed_queues_list"]
        assert catalog[0].annotations.read_only_hint is True
        request = {"operation": "queues.list", "workspace_id": workspace}
        result = await facade.call(object(), "managed_queues_list", request)
        assert not result.is_error
        assert result.structured_content == {
            "queues": [],
            "next_cursor": None,
            "server_time_ms": "1",
        }
        assert port.calls == 1
        assert port.thread_ids and event_loop_thread not in port.thread_ids
        assert policy.checks >= 2  # once while listing and again when called

        invalid_version = await facade.call(
            object(),
            "managed_queues_list",
            {**request, "schema_version": None},
        )
        assert invalid_version.is_error and port.calls == 1

        policy.enabled = False
        denied = await facade.call(object(), "managed_queues_list", request)
        assert denied.is_error and port.calls == 1
        policy.enabled = True
        port.enabled = False
        denied = await facade.call(object(), "managed_queues_list", request)
        assert denied.is_error and port.calls == 1

    asyncio.run(check())


def test_explicit_projections_drop_free_text_claims_logs_and_artifact_bytes():
    queue = {
        "workspace_id": str(uuid4()),
        "deployment": {
            "workspace_id": str(uuid4()),
            "deployment_id": str(uuid4()),
            "revision_id": "sha256:" + "a" * 64,
        },
        "queue_id": "queue",
    }
    item = {
        "queue": queue,
        "id": str(uuid4()),
        "queue_state": "IN_PROGRESS",
        "business_state": "ready",
        "label": "private label",
        "reason": "private reason",
        "payload": {"customer": "private"},
        "claim": {"owner_id": str(uuid4()), "epoch": 4},
        "worker_id": str(uuid4()),
        "created_ms": "1",
    }
    projected_item = _item_view(item)
    assert projected_item == {
        "id": item["id"],
        "queue_state": "IN_PROGRESS",
        "business_state": "ready",
        "created_ms": "1",
        "queue": {
            "workspace_id": queue["workspace_id"],
            "deployment": queue["deployment"],
            "queue_id": "queue",
        },
    }

    artifact = {
        "artifact": {
            "handle": "private-handle",
            "run_id": str(uuid4()),
            "digest": "sha256:" + "b" * 64,
            "size": 10,
        },
        "offset": 0,
        "data_base64": "secret-bytes",
        "eof": True,
        "next_cursor": None,
    }
    safe_artifact = _project_result(Operation.ARTIFACT, artifact)
    assert "data_base64" not in safe_artifact
    assert safe_artifact["artifact"] == artifact["artifact"]

    logs = _project_result(
        Operation.LOGS,
        {
            "run_id": str(uuid4()),
            "lines": [{"offset": 2, "text": "secret log"}],
            "next_cursor": None,
            "server_time_ms": "3",
        },
    )
    assert logs["lines"] == [{"offset": 2}]

    queues = _project_result(
        Operation.QUEUES,
        {
            "queues": [
                {
                    "queue": queue,
                    "mode": "producer",
                    "label": "private label",
                    "permissions": ["private permission"],
                    "counts": {"PENDING": 2, "IN_PROGRESS": 1, "private-label": 99},
                }
            ],
            "next_cursor": None,
            "server_time_ms": "4",
        },
    )
    assert queues["queues"][0]["counts"] == {"PENDING": 2, "IN_PROGRESS": 1}
    assert "label" not in queues["queues"][0]

    async def auth(_):
        return ManagedCaller(actor=Actor(principal_id=str(uuid4())))

    async def check():
        facade = ManagedWorkItemsMcp(object(), auth, object())
        denied = await facade.call(object(), "arbitrary_operation", {"operation": "items.claim"})
        assert denied.is_error

    asyncio.run(check())


def test_workspace_enumeration_has_a_hard_iteration_bound():
    workspace = str(uuid4())
    caller = ManagedCaller(actor=Actor(principal_id=str(uuid4())))

    class Policy:
        consumed = 0

        def workspaces(self, identity):
            assert identity == caller

            def repeated_forever():
                while True:
                    self.consumed += 1
                    yield workspace

            return repeated_forever()

        def allows(self, *_):
            raise AssertionError("oversized enumeration must be rejected first")

        def queues(self, *_):
            raise AssertionError("oversized enumeration must be rejected first")

    async def auth(_):
        return caller

    async def check():
        policy = Policy()
        facade = ManagedWorkItemsMcp(object(), auth, policy)
        assert await facade.tools(object()) == []
        assert policy.consumed == 101

    asyncio.run(check())


def test_model_facade_hides_review_and_retry_receipt_and_rejects_both_pre_service():
    workspace_id = str(uuid4())
    deployment_id = str(uuid4())
    package_id = str(uuid4())
    worker_id = str(uuid4())
    policy_id = str(uuid4())
    provider_id = str(uuid4())
    revision = "sha256:" + "a" * 64
    queue = {
        "workspace_id": workspace_id,
        "deployment": {
            "workspace_id": workspace_id,
            "deployment_id": deployment_id,
            "revision_id": revision,
        },
        "queue_id": "model-queue",
    }
    package_revision = {
        "workspace_id": workspace_id,
        "package_id": package_id,
        "revision_id": revision,
    }
    snapshot = {
        "deployment": queue["deployment"],
        "capability": {
            "package_revision": package_revision,
            "capability_id": "example",
        },
        "runtime_plan": {
            "package_revision": package_revision,
            "plan_digest": "plan-v1",
        },
        "worker": {
            "workspace_id": workspace_id,
            "worker_profile_id": worker_id,
            "revision_id": revision,
        },
        "policy": {
            "workspace_id": workspace_id,
            "policy_id": policy_id,
            "revision_id": revision,
        },
        "output_provider": {
            "workspace_id": workspace_id,
            "provider_profile_id": provider_id,
            "revision_id": revision,
        },
        "runtime_kind": "rcc",
        "capability_schema_digest": revision,
        "action_id": "example-action",
    }
    caller = ManagedCaller(actor=Actor(principal_id=str(uuid4())))

    class Policy:
        def workspaces(self, _):
            return [workspace_id]

        def allows(self, _, requested, operation):
            return str(requested.root) == workspace_id and operation in {
                Operation.ENQUEUE,
                Operation.CANCEL,
            }

        def queues(self, _, requested, operation):
            if str(requested.root) == workspace_id and operation in {
                Operation.ENQUEUE,
                Operation.CANCEL,
            }:
                return [QueueRef.model_validate_json(json.dumps(queue))]
            return []

    class Port:
        calls = 0

        def capabilities(self, _, requested):
            return Capabilities(
                runtime_version="1.1.0a13",
                sdk_version="0.5.0a1",
                workspace_id=requested,
                operations=(Operation.ENQUEUE, Operation.CANCEL),
                permissions=(Permission.ENQUEUE, Permission.CANCEL),
                backend="sqlite",
                modes=("producer",),
            )

        def call(self, *_):
            self.calls += 1
            raise AssertionError("model command must be rejected before domain call")

    async def auth(_):
        return caller

    async def check():
        port = Port()
        facade = ManagedWorkItemsMcp(port, auth, Policy())
        assert "review" not in _schema(Operation.ENQUEUE)["properties"]
        assert "reconciliation_receipt" not in _schema(Operation.CANCEL)["properties"]

        enqueue = {
            "operation": "items.enqueue",
            "idempotency_key": "model-enqueue",
            "queue": queue,
            "snapshot": snapshot,
            "payload": {"value": 1},
            "review": None,
        }
        cancel = {
            "operation": "items.cancel",
            "idempotency_key": "model-cancel",
            "queue": queue,
            "item_id": str(uuid4()),
            "expected_epoch": 1,
            "reason": "cancel requested",
            "reconciliation_receipt": None,
        }
        assert (await facade.call(object(), "managed_items_enqueue", enqueue)).is_error
        assert (await facade.call(object(), "managed_items_cancel", cancel)).is_error
        assert port.calls == 0

    asyncio.run(check())


def test_exact_queue_publication_is_rechecked_and_guessed_queue_never_reaches_port():
    workspace = str(uuid4())
    published_queue = _queue(workspace, "published")
    guessed_queue = _queue(workspace, "private")
    caller = ManagedCaller(actor=Actor(principal_id=str(uuid4())))

    class Policy:
        enabled = True

        def workspaces(self, _):
            return [workspace]

        def allows(self, _, requested, operation):
            return str(requested.root) == workspace and operation == Operation.LIST

        def queues(self, _, requested, operation):
            if not self.enabled or operation != Operation.LIST:
                return []
            return [published_queue]

    class Port:
        calls = 0

        def capabilities(self, _, requested):
            return Capabilities(
                runtime_version="1.1.0a13",
                sdk_version="0.5.0a1",
                workspace_id=requested,
                operations=(Operation.LIST,),
                permissions=(Permission.READ,),
                backend="sqlite",
                modes=("producer",),
            )

        def call(self, _, command):
            self.calls += 1
            assert command.queue == published_queue
            return {"items": [], "next_cursor": None, "server_time_ms": "1"}

    async def auth(_):
        return caller

    async def check():
        policy, port = Policy(), Port()
        facade = ManagedWorkItemsMcp(port, auth, policy)
        catalog = await facade.tools(object())
        assert [tool.name for tool in catalog] == ["managed_items_list"]
        request = {
            "operation": "items.list",
            "queue": published_queue.model_dump(mode="json"),
        }
        assert not (await facade.call(object(), "managed_items_list", request)).is_error
        guessed = {
            **request,
            "queue": guessed_queue.model_dump(mode="json"),
        }
        assert (await facade.call(object(), "managed_items_list", guessed)).is_error
        assert port.calls == 1

        # A previously discovered queue ceases to be callable after live
        # publication is revoked; catalog state is not cached by the facade.
        policy.enabled = False
        assert await facade.tools(object()) == []
        assert (await facade.call(object(), "managed_items_list", request)).is_error
        assert port.calls == 1

    asyncio.run(check())


def test_queue_listing_filters_unpublished_rows_and_hides_backend_cursor():
    workspace = str(uuid4())
    visible = _queue(workspace, "visible")
    hidden = _queue(workspace, "hidden")
    caller = ManagedCaller(actor=Actor(principal_id=str(uuid4())))

    class Policy:
        def workspaces(self, _):
            return [workspace]

        def allows(self, _, requested, operation):
            return str(requested.root) == workspace and operation == Operation.QUEUES

        def queues(self, _, requested, operation):
            return [visible] if operation == Operation.QUEUES else []

    class Port:
        calls = 0

        def capabilities(self, _, requested):
            return Capabilities(
                runtime_version="1.1.0a13",
                sdk_version="0.5.0a1",
                workspace_id=requested,
                operations=(Operation.QUEUES,),
                permissions=(Permission.READ,),
                backend="sqlite",
                modes=("producer",),
            )

        def call(self, _, command):
            self.calls += 1
            assert command.limit == 100
            if command.cursor is not None:
                assert command.cursor == "backend-hidden-inventory-cursor"
                return {
                    "queues": [],
                    "next_cursor": None,
                    "server_time_ms": "5",
                }
            return {
                "queues": [
                    {
                        "queue": visible.model_dump(mode="json"),
                        "label": "visible label",
                        "mode": "producer",
                        "counts": {"PENDING": 2},
                        "permissions": [Permission.READ.value],
                    },
                    {
                        "queue": hidden.model_dump(mode="json"),
                        "label": "hidden secret label",
                        "mode": "producer",
                        "counts": {"PENDING": 99},
                        "permissions": [Permission.READ.value],
                    },
                ],
                "next_cursor": "backend-hidden-inventory-cursor",
                "server_time_ms": "5",
            }

    async def auth(_):
        return caller

    async def check():
        port = Port()
        facade = ManagedWorkItemsMcp(port, auth, Policy())
        result = await facade.call(
            object(),
            "managed_queues_list",
            {"operation": "queues.list", "workspace_id": workspace, "limit": 1},
        )
        assert not result.is_error
        assert result.structured_content == {
            "queues": [
                {
                    "queue": visible.model_dump(mode="json"),
                    "mode": "producer",
                    "counts": {"PENDING": 2},
                }
            ],
            "next_cursor": None,
            "server_time_ms": "5",
        }
        serialized = json.dumps(result.structured_content)
        assert "hidden" not in serialized
        assert "backend-hidden-inventory-cursor" not in serialized
        assert port.calls == 2

    asyncio.run(check())


def test_queue_publication_iterator_is_bounded_and_fails_closed():
    workspace = str(uuid4())
    queue = _queue(workspace, "published")
    caller = ManagedCaller(actor=Actor(principal_id=str(uuid4())))

    class Policy:
        consumed = 0

        def workspaces(self, _):
            return [workspace]

        def allows(self, *_):
            raise AssertionError("unbounded queue scope must not reach capability checks")

        def queues(self, _, requested, operation):
            if operation != Operation.QUEUES:
                return []

            def infinite():
                while True:
                    self.consumed += 1
                    yield queue

            return infinite()

    class Port:
        calls = 0

        def capabilities(self, *_):
            self.calls += 1
            raise AssertionError("unbounded queue scope must fail before port access")

    async def auth(_):
        return caller

    async def check():
        policy, port = Policy(), Port()
        facade = ManagedWorkItemsMcp(port, auth, policy)
        assert await facade.tools(object()) == []
        assert policy.consumed == 101
        assert port.calls == 0
        denied = await facade.call(
            object(),
            "managed_queues_list",
            {"operation": "queues.list", "workspace_id": workspace},
        )
        assert denied.is_error
        assert policy.consumed == 202
        assert port.calls == 0

    asyncio.run(check())


def test_queue_cursor_paginates_only_recomputed_visible_set():
    workspace = str(uuid4())
    first = _queue(workspace, "first")
    second = _queue(workspace, "second")
    expected_order = sorted((first, second), key=_queue_key)
    hidden = _queue(workspace, "hidden")
    caller = ManagedCaller(actor=Actor(principal_id=str(uuid4())))

    class Policy:
        def workspaces(self, _):
            return [workspace]

        def allows(self, _, requested, operation):
            return str(requested.root) == workspace and operation == Operation.QUEUES

        def queues(self, _, requested, operation):
            return [first, second] if operation == Operation.QUEUES else []

    class Port:
        def capabilities(self, _, requested):
            return Capabilities(
                runtime_version="1.1.0a13",
                sdk_version="0.5.0a1",
                workspace_id=requested,
                operations=(Operation.QUEUES,),
                permissions=(Permission.READ,),
                backend="sqlite",
                modes=("producer",),
            )

        def call(self, _, command):
            assert command.cursor is None and command.limit == 100
            rows = [
                {
                    "queue": queue.model_dump(mode="json"),
                    "label": queue.queue_id,
                    "mode": "producer",
                    "counts": {"PENDING": 1},
                    "permissions": [Permission.READ.value],
                }
                for queue in (hidden, second, first)
            ]
            return {
                "queues": rows,
                "next_cursor": None,
                "server_time_ms": "7",
            }

    async def auth(_):
        return caller

    async def check():
        facade = ManagedWorkItemsMcp(Port(), auth, Policy())
        first_page = await facade.call(
            object(),
            "managed_queues_list",
            {"operation": "queues.list", "workspace_id": workspace, "limit": 1},
        )
        assert not first_page.is_error
        page = first_page.structured_content
        assert len(page["queues"]) == 1
        assert page["queues"][0]["queue"] == expected_order[0].model_dump(mode="json")
        cursor = page["next_cursor"]
        assert isinstance(cursor, str) and cursor
        assert "hidden" not in cursor and "backend" not in cursor

        second_page = await facade.call(
            object(),
            "managed_queues_list",
            {
                "operation": "queues.list",
                "workspace_id": workspace,
                "limit": 1,
                "cursor": cursor,
            },
        )
        assert not second_page.is_error
        assert [row["queue"]["queue_id"] for row in second_page.structured_content["queues"]] == [
            expected_order[1].queue_id
        ]
        assert second_page.structured_content["next_cursor"] is None

    asyncio.run(check())
