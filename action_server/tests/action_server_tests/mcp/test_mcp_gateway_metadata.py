import asyncio
import json
import uuid

from actions.server.mcp.gateway_metadata import (
    MCP_CORRELATION_ID_HEADER,
    MCP_METHOD_HEADER,
    MCP_NAME_HEADER,
    MCP_REQUEST_STATE_KEY,
    MCP_CORRELATION_ID_ATTRIBUTE,
    MCP_METHOD_ATTRIBUTE,
    MCP_NAME_ATTRIBUTE,
    McpRequestMetadataMiddleware,
    get_mcp_request_metadata,
)


def _request(body, headers=None):
    header_items = headers or []
    if isinstance(header_items, dict):
        header_items = list(header_items.items())
    encoded_body = (
        body if isinstance(body, (bytes, bytearray)) else json.dumps(body).encode()
    )
    return {
        "type": "http",
        "http_version": "1.1",
        "method": "POST",
        "path": "/mcp",
        "raw_path": b"/mcp",
        "query_string": b"",
        "headers": [
            (b"content-type", b"application/json"),
            *[(key.encode(), value.encode()) for key, value in header_items],
        ],
        "state": {},
        "body": encoded_body,
    }


async def _run(
    body,
    headers=None,
    receive_messages=None,
    observer=None,
    request_observer=None,
    read_past_end=False,
    replay_reads=0,
    response_headers=None,
    response_status=204,
):
    seen = {}

    async def app(scope, receive, send):
        seen["app_called"] = True
        seen["state"] = scope["state"]
        seen["context"] = get_mcp_request_metadata()
        if read_past_end:
            seen["received_after_body"] = await receive()
        if replay_reads:
            seen["replayed"] = [await receive() for _ in range(replay_reads)]
        await send(
            {
                "type": "http.response.start",
                "status": response_status,
                "headers": response_headers or [],
            }
        )
        await send({"type": "http.response.body", "body": b""})

    middleware_options = {}
    if observer is not None:
        middleware_options["metadata_observer"] = observer
    if request_observer is not None:
        middleware_options["request_observer"] = request_observer
    middleware = McpRequestMetadataMiddleware(app, **middleware_options)
    sent = []

    messages = receive_messages or [
        {"type": "http.request", "body": _request(body, headers)["body"]}
    ]

    async def receive():
        if messages:
            return messages.pop(0)
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        sent.append(message)

    await middleware(_request(body, headers), receive, send)
    return seen, sent


def test_exposes_validated_tool_identity_to_state_and_context():
    seen, sent = asyncio.run(
        _run(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {"name": "greet"},
            },
            {MCP_METHOD_HEADER: "tools/call", MCP_NAME_HEADER: "greet"},
        )
    )

    metadata = seen["state"][MCP_REQUEST_STATE_KEY]
    assert metadata.method == "tools/call"
    assert metadata.name == "greet"
    assert seen["context"] == metadata
    assert metadata.telemetry_attributes == {
        MCP_METHOD_ATTRIBUTE: "tools/call",
        MCP_NAME_ATTRIBUTE: "greet",
        MCP_CORRELATION_ID_ATTRIBUTE: metadata.correlation_id,
    }
    assert sent[0]["status"] == 204


def test_accepts_mcp_v2_and_future_method_names_without_a_finite_allowlist():
    for method, expected_method, expected_class in (
        ("server/discover", "server/discover", "server"),
        ("subscriptions/listen", "subscriptions/listen", "subscriptions"),
        ("vendor/future", "vendor/future", "extension"),
        ("line\nfeed", "line_feed", "extension"),
    ):
        seen, sent = asyncio.run(
            _run(
                {"jsonrpc": "2.0", "id": 1, "method": method},
                {MCP_METHOD_HEADER: method},
            )
        )
        metadata = seen["state"][MCP_REQUEST_STATE_KEY]
        assert metadata.method == expected_method
        assert metadata.method_classification == expected_class
        assert sent[0]["status"] == 204


def test_extracts_named_resource_and_prompt_from_validated_params():
    for method, params, name in (
        ("resources/read", {"uri": "resource://greet"}, "resource://greet"),
        ("prompts/get", {"name": "friendly"}, "friendly"),
    ):
        seen, _ = asyncio.run(
            _run(
                {"jsonrpc": "2.0", "id": 1, "method": method, "params": params},
                {MCP_METHOD_HEADER: method, MCP_NAME_HEADER: name},
            )
        )
        metadata = seen["state"][MCP_REQUEST_STATE_KEY]
        assert (metadata.method, metadata.name) == (method, name)


def test_batch_metadata_is_bounded_and_notifications_are_supported():
    seen, sent = asyncio.run(
        _run(
            [
                {"jsonrpc": "2.0", "method": "notifications/initialized"},
                {"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
            ],
            {MCP_METHOD_HEADER: "batch"},
        )
    )
    metadata = seen["state"][MCP_REQUEST_STATE_KEY]
    assert metadata.method == "batch"
    assert metadata.name is None


def test_batch_response_entries_do_not_break_request_metadata():
    seen, sent = asyncio.run(
        _run(
            [
                {"jsonrpc": "2.0", "id": 1, "result": {"ok": True}},
                {"jsonrpc": "2.0", "method": "notifications/initialized"},
            ],
            {MCP_METHOD_HEADER: "batch"},
        )
    )
    assert seen["state"][MCP_REQUEST_STATE_KEY].method == "notifications/initialized"
    assert sent[0]["status"] == 204


def test_response_only_batches_ignore_metadata_without_rejection():
    seen, sent = asyncio.run(
        _run(
            [
                {"jsonrpc": "2.0", "id": 1, "result": {"ok": True}},
                {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "error": {"code": -32600, "message": "bad"},
                },
            ],
            {
                MCP_METHOD_HEADER: "batch",
                MCP_NAME_HEADER: "arbitrary",
                MCP_CORRELATION_ID_HEADER: str(uuid.uuid4()),
            },
        )
    )
    assert seen["app_called"]
    assert not seen["state"]
    assert sent[0]["status"] == 204


def test_spoofed_or_inconsistent_identity_is_rejected():
    for headers in (
        {MCP_METHOD_HEADER: "tools/list"},
        {MCP_METHOD_HEADER: "tools/call", MCP_NAME_HEADER: "other"},
        {MCP_METHOD_HEADER: "client/secret", MCP_NAME_HEADER: "arbitrary"},
    ):
        seen, sent = asyncio.run(
            _run(
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/call",
                    "params": {"name": "greet"},
                },
                headers,
            )
        )
        assert "state" not in seen
        assert sent[0]["status"] == 400


def test_missing_headers_are_normalized_from_body():
    seen, sent = asyncio.run(
        _run(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {"name": "greet"},
            }
        )
    )
    metadata = seen["state"][MCP_REQUEST_STATE_KEY]
    assert (metadata.method, metadata.name) == ("tools/call", "greet")


def test_correlation_id_preserves_valid_uuid_and_generates_for_arbitrary_input():
    correlation_id = str(uuid.uuid4())
    seen, sent = asyncio.run(
        _run(
            {"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
            {MCP_CORRELATION_ID_HEADER: correlation_id},
        )
    )
    assert seen["state"][MCP_REQUEST_STATE_KEY].correlation_id == correlation_id

    seen, sent = asyncio.run(
        _run(
            {"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
            {MCP_CORRELATION_ID_HEADER: "not-a-safe-id"},
        )
    )
    generated = seen["state"][MCP_REQUEST_STATE_KEY].correlation_id
    assert generated != "not-a-safe-id"
    uuid.UUID(generated)
    assert (b"x-request-id", generated.encode()) in sent[0]["headers"]


def test_outer_authentication_rejects_before_metadata_parser():
    from starlette.authentication import AuthenticationBackend, AuthenticationError
    from starlette.middleware.authentication import AuthenticationMiddleware

    observed = []
    consumed = False

    class RejectingBackend(AuthenticationBackend):
        async def authenticate(self, _conn):
            raise AuthenticationError("unauthenticated")

    async def protected(_scope, _receive, _send):
        raise AssertionError("the protected MCP route must not be reached")

    guarded = AuthenticationMiddleware(
        McpRequestMetadataMiddleware(protected, metadata_observer=observed.append),
        backend=RejectingBackend(),
    )
    sent = []

    async def receive():
        nonlocal consumed
        consumed = True
        return {
            "type": "http.request",
            "body": b'{"method":"tools/call","secret":"do-not-read"}',
            "more_body": False,
        }

    async def send(message):
        sent.append(message)

    asyncio.run(
        guarded(
            _request(
                b'{"method":"tools/call","secret":"do-not-read"}',
                {MCP_METHOD_HEADER: "tools/call", MCP_NAME_HEADER: "secret"},
            ),
            receive,
            send,
        )
    )
    assert not consumed
    assert not observed
    assert sent[0]["status"] == 400


def test_valid_jsonrpc_responses_with_metadata_headers_reach_the_sdk():
    for body in (
        {"jsonrpc": "2.0", "id": 1, "result": {"ok": True}},
        {"jsonrpc": "2.0", "id": 1, "error": {"code": -32600, "message": "bad"}},
    ):
        seen, sent = asyncio.run(
            _run(
                body,
                {
                    MCP_METHOD_HEADER: "tools/call",
                    MCP_NAME_HEADER: "secret",
                },
            )
        )
        assert seen["app_called"]
        assert not seen["state"]
        assert sent[0]["status"] == 204


def test_fragmented_body_is_replayed_and_empty_after_downstream_reads_past_end():
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list"}).encode()
    seen, _ = asyncio.run(
        _run(
            None,
            receive_messages=[
                {"type": "http.request", "body": body[:9], "more_body": True},
                {"type": "http.request", "body": body[9:], "more_body": False},
            ],
            replay_reads=3,
        )
    )
    assert [chunk["body"] for chunk in seen["replayed"][:2]] == [body[:9], body[9:]]
    assert seen["replayed"][2] == {
        "type": "http.request",
        "body": b"",
        "more_body": False,
    }


def test_oversized_body_is_rejected_without_forwarding_body():
    seen, sent = asyncio.run(
        _run(
            None,
            receive_messages=[
                {
                    "type": "http.request",
                    "body": b"x" * (1024 * 1024 + 1),
                    "more_body": False,
                }
            ],
        )
    )
    assert not seen.get("app_called", False)
    assert sent[0]["status"] == 413


def test_body_at_one_mib_is_forwarded():
    seen, sent = asyncio.run(_run(b"x" * (1024 * 1024)))
    assert seen["app_called"]
    assert sent[0]["status"] == 204


def test_declared_oversized_body_is_rejected_before_consumption():
    seen, sent = asyncio.run(
        _run(
            b"{}",
            [("content-length", str(1024 * 1024 + 1))],
        )
    )
    assert not seen.get("app_called", False)
    assert sent[0]["status"] == 413


def test_disconnect_messages_are_replayed_to_the_sdk():
    seen, _ = asyncio.run(
        _run(
            None,
            receive_messages=[{"type": "http.disconnect"}],
            replay_reads=1,
        )
    )
    assert seen["replayed"] == [{"type": "http.disconnect"}]


def test_untrusted_jsonrpc_shapes_never_become_metadata():
    for method in ([], {}, 1, "", "x" * 257):
        seen, sent = asyncio.run(
            _run(
                {"jsonrpc": "2.0", "id": 1, "method": method},
                {MCP_METHOD_HEADER: "tools/list"},
            )
        )
        assert "state" not in seen
        assert sent[0]["status"] == 400

    seen, sent = asyncio.run(
        _run(
            {"id": 1, "method": "tools/list"},
            {MCP_METHOD_HEADER: "tools/list"},
        )
    )
    assert "state" not in seen
    assert sent[0]["status"] == 400


def test_parser_failures_are_forwarded_without_a_middleware_500():
    deep_json = b"[" * 2048 + b"]" * 2048
    huge_id = b'{"jsonrpc":"2.0","id":' + b"9" * 5000 + b',"method":"tools/list"}'
    for body, headers in (
        (deep_json, None),
        (huge_id, {MCP_METHOD_HEADER: "tools/list"}),
    ):
        seen, sent = asyncio.run(_run(body, headers))
        assert seen["app_called"]
        assert sent[0]["status"] == 204


def test_oversized_name_is_rejected_without_trusting_header():
    seen, sent = asyncio.run(
        _run(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {"name": "x" * 257},
            },
            [(MCP_METHOD_HEADER, "tools/call"), (MCP_NAME_HEADER, "x" * 257)],
        )
    )
    assert "state" not in seen
    assert sent[0]["status"] == 400


def test_duplicate_identity_headers_are_rejected_case_insensitively():
    for headers in (
        [("Mcp-Method", "tools/list"), ("mcp-method", "tools/list")],
        [("Mcp-Name", "one"), ("MCP-NAME", "one")],
        [("X-Request-ID", str(uuid.uuid4())), ("x-request-id", str(uuid.uuid4()))],
    ):
        _, sent = asyncio.run(
            _run({"jsonrpc": "2.0", "id": 1, "method": "tools/list"}, headers)
        )
        assert sent[0]["status"] == 400


def test_correlation_id_is_propagated_on_response_and_observed_by_consumer():
    correlation_id = str(uuid.uuid4())
    observed = []
    seen, sent = asyncio.run(
        _run(
            {"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
            [(MCP_CORRELATION_ID_HEADER, correlation_id)],
            observer=observed.append,
        )
    )
    assert observed == [seen["state"][MCP_REQUEST_STATE_KEY]]
    assert (b"x-request-id", correlation_id.encode()) in sent[0]["headers"]


def test_response_request_id_replaces_downstream_duplicates_case_insensitively():
    correlation_id = str(uuid.uuid4())
    _, sent = asyncio.run(
        _run(
            {"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
            {MCP_CORRELATION_ID_HEADER: correlation_id},
            response_headers=[
                (b"X-Request-ID", b"downstream-one"),
                (b"x-request-id", b"downstream-two"),
                (b"x-preserve", b"yes"),
            ],
        )
    )
    request_ids = [
        (key, value)
        for key, value in sent[0]["headers"]
        if key.lower() == MCP_CORRELATION_ID_HEADER.encode()
    ]
    assert request_ids == [(b"x-request-id", correlation_id.encode())]
    assert (b"x-preserve", b"yes") in sent[0]["headers"]


def test_observability_record_is_bounded_redacted_and_has_outcome_fields():
    records = []
    raw_uri = (
        "https://user:password@example.test/readable/"
        + "x" * 120
        + "?token=do-not-log#fragment"
    )
    correlation_id = str(uuid.uuid4())
    _, sent = asyncio.run(
        _run(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "resources/read",
                "params": {"uri": raw_uri},
            },
            {
                MCP_METHOD_HEADER: "resources/read",
                MCP_NAME_HEADER: raw_uri,
                MCP_CORRELATION_ID_HEADER: correlation_id,
            },
            request_observer=records.append,
            response_status=503,
        )
    )
    assert sent[0]["status"] == 503
    assert len(records) == 1
    attributes = records[0].telemetry_attributes
    assert attributes["actions.mcp.method"] == "resources/read"
    assert attributes["actions.mcp.method_class"] == "resources"
    assert attributes["actions.mcp.status_code"] == 503
    assert attributes["actions.mcp.latency_ms"] >= 0
    assert attributes["actions.correlation_id"] == correlation_id
    assert len(attributes["actions.mcp.name"]) <= 128
    assert "password" not in str(attributes)
    assert "token" not in str(attributes)
    assert "do-not-log" not in str(attributes)
    assert raw_uri not in str(attributes)


def test_observer_exceptions_are_non_fatal_and_do_not_emit_request_data(caplog):
    def fail_metadata_observer(_metadata):
        raise OverflowError("body-secret")

    def fail_request_observer(_observation):
        raise RecursionError("credential-secret")

    seen, sent = asyncio.run(
        _run(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {"name": "greet"},
            },
            {MCP_METHOD_HEADER: "tools/call", MCP_NAME_HEADER: "greet"},
            observer=fail_metadata_observer,
            request_observer=fail_request_observer,
        )
    )
    assert seen["app_called"]
    assert sent[0]["status"] == 204
    assert "OverflowError" in caplog.text
    assert "RecursionError" in caplog.text
    assert "body-secret" not in caplog.text
    assert "credential-secret" not in caplog.text


def test_whitespace_around_identity_values_is_rejected():
    _, sent = asyncio.run(
        _run(
            {"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
            [(MCP_METHOD_HEADER, " tools/list")],
        )
    )
    assert sent[0]["status"] == 400


def test_malformed_json_without_metadata_headers_preserves_downstream_status():
    seen = {}

    async def app(scope, receive, send):
        seen["body"] = (await receive())["body"]
        await send({"type": "http.response.start", "status": 422, "headers": []})
        await send({"type": "http.response.body", "body": b"protocol error"})

    async def receive():
        return {"type": "http.request", "body": b"not-json", "more_body": False}

    sent = []

    async def send(message):
        sent.append(message)

    asyncio.run(McpRequestMetadataMiddleware(app)(_request(None), receive, send))
    assert seen["body"] == b"not-json"
    assert sent[0]["status"] == 422


def test_outer_auth_gate_rejects_without_consuming_request_body():
    consumed = False

    async def protected(scope, receive, send):
        await send({"type": "http.response.start", "status": 403, "headers": []})
        await send({"type": "http.response.body", "body": b"forbidden"})

    async def receive():
        nonlocal consumed
        consumed = True
        return {"type": "http.request", "body": b"secret", "more_body": False}

    sent = []

    async def send(message):
        sent.append(message)

    asyncio.run(protected(_request(None), receive, send))
    assert not consumed
    assert sent[0]["status"] == 403


def test_request_context_isolated_across_concurrent_requests():
    observed = {}
    records = []

    async def app(scope, receive, send):
        request_id = scope["headers"][-1][1].decode()
        observed[request_id] = get_mcp_request_metadata()
        await asyncio.sleep(0)
        assert get_mcp_request_metadata() == observed[request_id]
        await send({"type": "http.response.start", "status": 204, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    async def observe(record):
        records.append(record)
        await asyncio.sleep(0)
        assert get_mcp_request_metadata() == record.metadata

    async def run(request_id):
        middleware = McpRequestMetadataMiddleware(app, request_observer=observe)
        sent = []

        async def receive():
            return {
                "type": "http.request",
                "body": json.dumps(
                    {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}
                ).encode(),
            }

        async def send(message):
            sent.append(message)

        await middleware(
            _request(
                {"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
                [(MCP_CORRELATION_ID_HEADER, request_id)],
            ),
            receive,
            send,
        )

    ids = [str(uuid.uuid4()), str(uuid.uuid4())]

    async def run_all():
        await asyncio.gather(*(run(request_id) for request_id in ids))

    asyncio.run(run_all())
    assert {metadata.correlation_id for metadata in observed.values()} == set(ids)
    assert {record.metadata.correlation_id for record in records} == set(ids)
    assert {record.status_code for record in records} == {204}


def test_cors_exposes_the_canonical_mcp_request_id(tmp_path, monkeypatch):
    from fastapi.middleware.cors import CORSMiddleware

    from actions.server._app import get_app
    from actions.server._settings import Settings

    monkeypatch.setattr(
        "actions.server._settings._global_settings",
        Settings(artifacts_dir=tmp_path, datadir=tmp_path),
    )
    get_app.cache_clear()
    try:
        app = get_app()
        cors = next(
            middleware
            for middleware in app.user_middleware
            if middleware.cls is CORSMiddleware
        )
        assert "X-Request-ID" in cors.kwargs["expose_headers"]
    finally:
        get_app.cache_clear()
